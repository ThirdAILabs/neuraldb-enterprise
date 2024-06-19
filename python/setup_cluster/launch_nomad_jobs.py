from setup_cluster.ssh_client_handler import SSHClientHandler
import os
import tempfile
import requests


class NomadJobDeployer:
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger

        self.security = self.config.get("security", {})
        self.api = self.config.get("api", {})
        self.autoscaling = self.config.get("autoscaling", {})

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

        sql_server_node = next(
            node for node in self.config["nodes"] if "sql_server" in node
        )
        self.sql_server_database_password = sql_server_node["sql_server"][
            "database_password"
        ]
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
        command = "grep 'Secret ID' /opt/neuraldb_enterprise/nomad_data/task_runner_token.txt | awk '{print $NF}'"

        use_jump = self.nomad_server_private_ip != self.web_ingress_private_ip
        ip = self.nomad_server_private_ip if use_jump else self.web_ingress_public_ip
        return self.ssh_client_handler.execute_commands(
            [command], ip if use_jump else self.web_ingress_public_ip, use_jump
        )

    def submit_nomad_job(self, nomad_ip, hcl_template, **kwargs):

        def replace_placeholders(filepath, replacements):
            with open(filepath, "r") as file:
                content = file.read()

            self.logger.info(f"Initial Content: {content}")
            self.logger.info(f"Replacement Content: {kwargs}")
            for key, value in replacements.items():
                content = content.replace(f"{{{{ {key} }}}}", str(value))

            temp_file = tempfile.NamedTemporaryFile(delete=False, mode="w")
            temp_file_path = temp_file.name

            self.logger.info(f"Final Content: {content}")
            # Write the modified content to the temporary file
            with open(temp_file_path, "w") as temp_file:
                temp_file.write(content)

            return temp_file_path

        # Function to submit job to Nomad
        def submit_to_nomad(hcl_file_path, nomad_endpoint, token):
            headers = {"Content-Type": "application/json", "X-Nomad-Token": token}
            hcl_to_json_url = f"{nomad_endpoint}v1/jobs/parse"
            submit_job_url = f"{nomad_endpoint}v1/jobs"

            with open(hcl_file_path, "r") as file:
                hcl_content = file.read()

            # Convert HCL to JSON using the Nomad API
            response = requests.post(
                hcl_to_json_url,
                headers=headers,
                json={"JobHCL": hcl_content, "Canonicalize": True},
            )
            job_json = response.json()

            # Submit the job JSON to Nomad
            final_response = requests.post(
                submit_job_url, headers=headers, json={"Job": job_json}
            )
            self.logger.info(final_response.text)  # Log the response for debugging

            # Cleanup the temporary file
            os.remove(hcl_file_path)

        nomad_endpoint = f"http://{nomad_ip}:4646/"
        temp_hcl_path = replace_placeholders(hcl_template, kwargs)
        submit_to_nomad(temp_hcl_path, nomad_endpoint, kwargs["TASK_RUNNER_TOKEN"])

    def deploy_jobs(self):
        """Deploy all necessary jobs to the Nomad server."""
        acl_token = (
            self.get_acl_token()
        )  # Assuming get_acl_token() fetches a valid ACL token
        self.logger.info(f"ACL TOKEN: {acl_token}")
        # TODO(pratik): Add an error, whenever acl_token is empty.
        # Deploy the Traefik job
        self.submit_nomad_job(
            self.web_ingress_public_ip,
            "../nomad/nomad_jobs/traefik_job.hcl.tpl",
            TASK_RUNNER_TOKEN=acl_token,
            PRIVATE_SERVER_IP=self.nomad_server_private_ip,
            NODE_POOL=self.node_pool,
        )

        # Deploy the Model Bazaar job
        self.submit_nomad_job(
            self.web_ingress_public_ip,
            "../nomad/nomad_jobs/model_bazaar_job.hcl.tpl",
            TASK_RUNNER_TOKEN=acl_token,
            DB_PASSWORD=self.sql_server_database_password,
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
        )

        # Deploy the Nomad Autoscaler job
        self.submit_nomad_job(
            self.web_ingress_public_ip,
            "../nomad/nomad_jobs/nomad_autoscaler_job.hcl",
            TASK_RUNNER_TOKEN=acl_token,
        )
