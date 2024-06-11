import json
import paramiko


class SQLServerDeployer:
    def __init__(self, config):
        self.config = config

        self.sql_server_private_ip = next(
            node["private_ip"] for node in self.config["nodes"] if "sql_server" in node
        )
        sql_server_node = next(
            node for node in self.config["nodes"] if "sql_server" in node
        )
        self.sql_server_database_dir = sql_server_node["sql_server"]["database_dir"]
        self.sql_server_database_password = sql_server_node["sql_server"][
            "database_password"
        ]
        self.sql_client_private_ips = [
            node["private_ip"]
            for node in self.config["nodes"]
            if node["private_ip"] != self.sql_server_private_ip
        ]

        web_ingress = next(
            node for node in self.config["nodes"] if "web_ingress" in node
        )
        self.web_ingress_private_ip = web_ingress["private_ip"]
        self.web_ingress_public_ip = web_ingress["web_ingress"]["public_ip"]
        self.node_ssh_username = self.config["ssh_username"]
        self.web_ingress_ssh_username = web_ingress["web_ingress"]["ssh_username"]

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

        self.ssh.close()

    def deploy_sql_server(self):
        if self.web_ingress_private_ip == self.sql_server_private_ip:
            ssh_host = self.web_ingress_public_ip
            ssh_username = self.web_ingress_ssh_username
            proxy = None
        else:
            ssh_host = self.sql_server_private_ip
            ssh_username = self.node_ssh_username
            proxy = f"ssh -o StrictHostKeyChecking=no -J {self.web_ingress_ssh_username}@{self.web_ingress_public_ip} {self.node_ssh_username}@{self.sql_server_private_ip}"

        commands = [
            f"sudo mkdir -p {self.sql_server_database_dir}/docker-postgres-init",
            f"sudo mkdir -p {self.sql_server_database_dir}/data",
            f"cd {self.sql_server_database_dir}/docker-postgres-init",
            f"sudo tee init-db.sh > /dev/null <<'EOD'\n#!/bin/bash\n{{\n    echo 'host  all all 172.17.0.0/16  md5'\n    for IP in {self.sql_client_private_ips}:\n        echo 'host  all all $IP/32  md5'\n}} >> \"$PGDATA/pg_hba.conf\"\nEOD",
            "sudo chmod +x init-db.sh",
            "sudo docker pull postgres",
            "sudo docker stop neuraldb-enterprise-postgresql-server || true",
            "sudo docker rm neuraldb-enterprise-postgresql-server || true",
            f"sudo docker run -d --name neuraldb-enterprise-postgresql-server -e POSTGRES_PASSWORD={self.sql_server_database_password} -e POSTGRES_DB=modelbazaar -e POSTGRES_USER=modelbazaaruser -v {self.sql_server_database_dir}/docker-postgres-init:/docker-entrypoint-initdb.d -v {self.sql_server_database_dir}/data:/var/lib/postgresql/data -p 5432:5432 postgres",
        ]

        self.ssh_command(ssh_host, ssh_username, commands, proxy)
