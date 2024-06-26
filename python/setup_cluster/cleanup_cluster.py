from setup_cluster.ssh_client_handler import SSHClientHandler
import requests


class CleanupSelfHostedCluster:
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.ssh_client_handler = SSHClientHandler(
            self.config["ssh_username"],
            self.config["web_ingress"]["ssh_username"],
            self.config["web_ingress"]["public_ip"],
            self.config["web_ingress"]["private_ip"],
            logger,
        )

    def cleanup_services(self):
        cleanup_commands = {
            "sql_server": f"sudo docker stop neuraldb-enterprise-postgresql-server || true && sudo docker rm neuraldb-enterprise-postgresql-server || true && sudo rm -rf {self.config['sql_server']['database_dir']}/*",
        }

        for node in self.config["nodes"]:
            if "sql_server" in node:
                ip = node["private_ip"]
                self.logger.info(f"Cleaning up SQL Server on {ip}")
                self.ssh_client_handler.execute_commands(
                    [cleanup_commands["sql_server"]], ip
                )
        
        self.logger.info("Cleanup completed successfully.")

    def cleanup_nomad_setup(self):
        self.logger.info("Starting cleanup of Nomad setup...")
        cleanup_commands = [
            "sudo systemctl stop nomad",
            "sudo systemctl disable nomad",
            "sudo rm -rf /etc/nomad.d",
            "sudo rm -rf /opt/nomad",
            "sudo rm -rf /var/lib/nomad",
            "tmux kill-session -t nomad-agent",
        ]

        for ip in [
            node["private_ip"]
            for node in self.config["nodes"]
            if "nomad_server" in node or "nomad_client" in node
        ]:
            self.logger.info(f"Cleaning up Nomad on {ip}")
            self.ssh_client_handler.execute_commands(
                cleanup_commands,
                ip,
                use_jump=(self.config["web_ingress"]["private_ip"] != ip),
            )

        self.logger.info("Nomad cleanup completed successfully.")

    def cleanup_nomad_jobs(self):
        nomad_ip = self.config["web_ingress"]["public_ip"]
        nomad_api_endpoint = f"http://{nomad_ip}:4646/v1/jobs"

        job_ids = ["traefik", "model-bazaar", "nomad-autoscaler"]

        for job_id in job_ids:
            try:
                response = requests.delete(f"{nomad_api_endpoint}/{job_id}?purge=true")
                if response.status_code == 200:
                    self.logger.info(f"Successfully deregistered job {job_id}")
                else:
                    self.logger.error(
                        f"Failed to deregister job {job_id}: {response.text}"
                    )
            except Exception as e:
                self.logger.error(
                    f"Error when trying to deregister job {job_id}: {str(e)}"
                )

        self.logger.info("Nomad jobs cleanup completed successfully.")
        
    def cleanup_nfs_setup(self):
        self.logger.info("Starting NFS cleanup...")
        shared_node = next(node for node in self.config["nodes"] if "shared_file_system" in node)
        nfs_server_ip = shared_node["private_ip"]
        shared_dir = shared_node["shared_file_system"]["shared_dir"]
        
        remove_exports_command = [
            "sudo exportfs -ua",
            "sudo sed -i '/" + shared_dir.replace("/", "\/") + "/d' /etc/exports",
            "sudo systemctl restart nfs-kernel-server"
        ]
        self.ssh_client_handler.execute_commands(
            remove_exports_command,
            nfs_server_ip,
            use_jump=(self.config["web_ingress"]["private_ip"] != nfs_server_ip)
        )
        
        nfs_client_private_ips = [
            node["private_ip"]
            for node in self.config["nodes"]
            if node["private_ip"] != nfs_server_ip
        ]
        for client_ip in nfs_client_private_ips:
            unmount_nfs_command = [
                f"sudo umount -l {shared_dir}",
                f"sudo sed -i '/{nfs_server_ip.replace('.', '\.')}:\/{shared_dir.replace('/', '\/')}/d' /etc/fstab"
            ]
            self.ssh_client_handler.execute_commands(
                unmount_nfs_command,
                client_ip,
                use_jump=(self.config["web_ingress"]["private_ip"] != client_ip)
            )

        self.logger.info("NFS cleanup completed successfully.")