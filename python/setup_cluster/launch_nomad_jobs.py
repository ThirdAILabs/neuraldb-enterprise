from setup_cluster.ssh_client_handler import SSHClientHandler
import os
import tempfile
import json


class NomadJobDeployer:
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger

        self.security = self.config.get("security", {})
        self.api = self.config.get("api", {})
        self.autoscaling = self.config.get("autoscaling", {})

        self.ndb_enterprise_version = self.config["ndb_enterprise_version"]

        self.shared_file_system_private_ip = next(
            node["private_ip"]
            for node in self.config["nodes"]
            if "shared_file_system" in node
        )

        web_ingress = next(
            node for node in self.config["nodes"] if "web_ingress" in node
        )
        self.web_ingress_private_ip = web_ingress["private_ip"]
        self.web_ingress_public_ip = web_ingress["web_ingress"]["public_ip"]
        self.web_ingress_ssh_username = web_ingress["web_ingress"]["ssh_username"]

        self.nomad_server_private_ip = next(
            node["private_ip"]
            for node in self.config["nodes"]
            if "nomad_server" in node
        )
        self.node_ssh_username = self.config["ssh_username"]

        self.sql_uri = self.config["sql_uri"]
        shared_file_system_node = next(
            node for node in self.config["nodes"] if "shared_file_system" in node
        )
        self.shared_dir = shared_file_system_node["shared_file_system"]["shared_dir"]

        self.node_pool = (
            "default"
            if web_ingress.get("web_ingress", {}).get("run_jobs", True)
            else "web_ingress"
        )

        self.jwt_secret = self.security["jwt_secret"]
        self.admin_username = self.security["admin"]["username"]
        self.admin_mail = self.security["admin"]["email"]
        self.admin_password = self.security["admin"]["password"]
        self.genai_key = self.api["genai_key"]
        self.autoscaling_enabled = str(self.autoscaling["enabled"]).lower()
        self.autoscaler_max_count = str(self.autoscaling["max_count"])

        self.ssh_client_handler = SSHClientHandler(
            self.node_ssh_username,
            self.web_ingress_ssh_username,
            self.web_ingress_public_ip,
            web_ingress_private_ip=self.web_ingress_private_ip,
            logger=logger,
        )

    def get_acl_token(self):
        """
        Retrieves the ACL token needed for authentication with a Nomad server.

        Returns:
            str: The ACL token retrieved via SSH command execution.
        """

        command = "grep 'Secret ID' /opt/neuraldb_enterprise/nomad_data/task_runner_token.txt | awk '{print $NF}'"

        use_jump = self.nomad_server_private_ip != self.web_ingress_private_ip
        ip = self.nomad_server_private_ip if use_jump else self.web_ingress_public_ip
        return self.ssh_client_handler.execute_commands(
            [command], ip if use_jump else self.web_ingress_public_ip, use_jump
        )

    def submit_nomad_job(self, hcl_template, acl_token, **kwargs):
        """
        Submits a job to the Nomad server using an HCL template and SSH connections handled by SSHClientHandler.

        Parameters:
            hcl_template (str): The filepath to the HCL template.
            acl_token (str): ACL token for authentication with the Nomad API.
        """

        def replace_placeholders(filepath, replacements):
            """
            Replaces placeholders in the file specified by 'filepath' with 'replacements'.
            """
            with open(filepath, "r") as file:
                content = file.read()

            self.logger.info(f"Initial Content: {content}")
            for key, value in replacements.items():
                content = content.replace(f"{{{{ {key} }}}}", str(value))

            temp_file = tempfile.NamedTemporaryFile(delete=False, mode="w")
            temp_file_path = temp_file.name
            with open(temp_file_path, "w") as temp_file:
                temp_file.write(content)

            return temp_file_path

        def submit_to_nomad_via_ssh(temp_hcl_path, acl_token):
            """
            Submits a job to Nomad using the SSH connection handled by SSHClientHandler.
            """
            hcl_to_json_url = "http://localhost:4646/v1/jobs/parse"
            submit_job_url = "http://localhost:4646/v1/jobs"

            try:
                # Reading HCL file content
                with open(temp_hcl_path, "r") as file:
                    hcl_content = file.read()

                # Convert HCL to JSON payload
                hcl_payload = json.dumps({"JobHCL": hcl_content, "Canonicalize": True})
                json_payload = self.ssh_client_handler.execute_commands(
                    [
                        f"curl -s -X POST -H 'Content-Type: application/json' -H 'X-Nomad-Token: {acl_token}' -d '{hcl_payload}' '{hcl_to_json_url}'"
                    ],
                    self.web_ingress_private_ip,
                    use_jump=True,
                )
                self.logger.info(f"Converted JSON Payload: {json_payload}")

                # Submit the JSON payload to Nomad
                final_response = self.ssh_client_handler.execute_commands(
                    [
                        f"curl -s -X POST -H 'Content-Type: application/json' -H 'X-Nomad-Token: {acl_token}' -d '{{\"Job\":{json_payload}}}' '{submit_job_url}'"
                    ],
                    self.web_ingress_private_ip,
                    use_jump=True,
                )
                self.logger.info(f"Nomad Submission Response: {final_response}")
            finally:
                # Cleanup the temporary file
                os.remove(temp_hcl_path)

        # Main process
        temp_hcl_path = replace_placeholders(hcl_template, kwargs)
        submit_to_nomad_via_ssh(temp_hcl_path, acl_token)

    def deploy_jobs(self):
        """
        Deploys multiple predefined Nomad jobs to Nomad server

        This function sequentially deploys multiple services by fetching the required ACL token,
        submitting different Nomad job configurations using HCL templates, and handling dependencies
        and configurations for each service.
        """

        acl_token = (
            self.get_acl_token()
        )  # Assuming get_acl_token() fetches a valid ACL token

        self.logger.info(f"ACL TOKEN: {acl_token}")
        if acl_token == "":
            raise ValueError(
                "TASK RUNNER TOKEN cannot be retrieved. There are issues with nomad initialization."
            )
        # Deploy the Traefik job
        self.submit_nomad_job(
            "../nomad/nomad_jobs/traefik_job.hcl.tpl",
            acl_token,
            PRIVATE_SERVER_IP=self.nomad_server_private_ip,
            NODE_POOL=self.node_pool,
        )

        # Deploy the Model Bazaar job
        self.submit_nomad_job(
            "../nomad/nomad_jobs/model_bazaar_job.hcl.tpl",
            acl_token,
            SHARE_DIR=self.shared_dir,
            PUBLIC_SERVER_IP=self.web_ingress_public_ip,
            PRIVATE_SERVER_IP=self.nomad_server_private_ip,
            JWT_SECRET=self.jwt_secret,
            ADMIN_USERNAME=self.admin_username,
            ADMIN_MAIL=self.admin_mail,
            ADMIN_PASSWORD=self.admin_password,
            AUTOSCALING_ENABLED=self.autoscaling_enabled,
            AUTOSCALER_MAX_COUNT=self.autoscaler_max_count,
            GENAI_KEY=self.genai_key,
            NDBE_VERSION=self.ndb_enterprise_version,
        )

        # Deploy the Nomad Autoscaler job
        self.submit_nomad_job(
            "../nomad/nomad_jobs/nomad_autoscaler_job.hcl",
            acl_token,
        )
