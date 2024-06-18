from setup_cluster.ssh_client_handler import SSHClientHandler


class SQLServerDeployer:
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger

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

        self.ssh_client_handler = SSHClientHandler(
            self.node_ssh_username,
            self.web_ingress_ssh_username,
            self.web_ingress_public_ip,
            web_ingress_private_ip=self.web_ingress_private_ip,
            logger=logger,
        )

    def deploy_sql_server(self):
        ip_list = " ".join(self.sql_client_private_ips)
        # Also added command to clean postgreql database
        commands = f"""
sudo rm -rf {self.sql_server_database_dir}/*
sudo mkdir -p {self.sql_server_database_dir}/docker-postgres-init
sudo mkdir -p {self.sql_server_database_dir}/data
cd {self.sql_server_database_dir}/docker-postgres-init
sudo tee init-db.sh > /dev/null <<'EOD'
#!/bin/bash
{{
    echo 'host  all all 172.17.0.0/16  md5'
    for IP in {ip_list}
    do
        echo "host  all all $IP/32  md5"
    done
}} >> "$PGDATA/pg_hba.conf"
EOD
sudo chmod +x init-db.sh
sudo docker pull postgres
sudo docker stop neuraldb-enterprise-postgresql-server || true
sudo docker rm neuraldb-enterprise-postgresql-server || true
sudo docker run -d --name neuraldb-enterprise-postgresql-server -e POSTGRES_PASSWORD={self.sql_server_database_password} -e POSTGRES_DB=modelbazaar -e POSTGRES_USER=modelbazaaruser -v {self.sql_server_database_dir}/docker-postgres-init:/docker-entrypoint-initdb.d -v {self.sql_server_database_dir}/data:/var/lib/postgresql/data -p 5432:5432 postgres
"""
        use_jump = self.web_ingress_private_ip != self.sql_server_private_ip
        self.ssh_client_handler.execute_commands(
            [commands],
            self.sql_server_private_ip if use_jump else self.web_ingress_public_ip,
            use_jump,
        )
