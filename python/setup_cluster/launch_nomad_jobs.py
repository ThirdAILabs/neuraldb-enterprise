import json
import paramiko
import os


class NomadJobDeployer:
    def __init__(self, config):
        self.config = config

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

        self.initialize_ssh_client()

    def initialize_ssh_client(self):
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    def close_ssh_connection(self):
        """Close the SSH connection if it is open."""
        try:
            if self.ssh.get_transport() and self.ssh.get_transport().is_active():
                self.ssh.close()
        except Exception as e:
            print(f"Failed to close SSH connection: {e}")

    def ssh_command(self, host, username, commands, proxy=None):
        if proxy:
            proxy = paramiko.ProxyCommand(proxy)
            self.ssh.connect(hostname=host, username=username, sock=proxy)
        else:
            self.ssh.connect(hostname=host, username=username)

        for command in commands:
            stdin, stdout, stderr = self.ssh.exec_command(command)
            print(stdout.read().decode())
            print(stderr.read().decode())

    def get_acl_token(self):
        if self.web_ingress_private_ip == self.nomad_server_private_ip:
            ssh_host = self.web_ingress_public_ip
            ssh_username = self.web_ingress_ssh_username
            proxy = None
        else:
            ssh_host = self.nomad_server_private_ip
            ssh_username = self.node_ssh_username
            proxy = f"ssh -o StrictHostKeyChecking=no -J {self.web_ingress_ssh_username}@{self.web_ingress_public_ip} {self.node_ssh_username}@{self.nomad_server_private_ip}"

        command = "grep 'Secret ID' \"/opt/neuraldb_enterprise/nomad_data/task_runner_token.txt\" | awk '{print $NF}'"
        stdin, stdout, stderr = self.ssh.exec_command(command)
        acl_token = stdout.read().decode().strip()
        return acl_token

    def submit_nomad_job(self, job_template, **kwargs):
        command = f"bash ../nomad/nomad_jobs/submit_nomad_job.sh {self.web_ingress_public_ip} {job_template} {self.acl_token}"
        for key, value in kwargs.items():
            command += f" {key}={value}"
        self.ssh_command(
            self.nomad_server_private_ip, self.node_ssh_username, [command]
        )

    def deploy_jobs(self):
        self.acl_token = self.get_acl_token()

        self.submit_nomad_job(
            "../nomad/nomad_jobs/traefik_job.hcl.tpl",
            PRIVATE_SERVER_IP=self.nomad_server_private_ip,
            NODE_POOL=self.node_pool,
        )
        self.submit_nomad_job(
            "../nomad/nomad_jobs/model_bazaar_job.hcl.tpl",
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
        self.submit_nomad_job(
            "../nomad/nomad_jobs/nomad_autoscaler_job.hcl",
        )
