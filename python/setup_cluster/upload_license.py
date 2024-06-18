from setup_cluster.ssh_client_handler import SSHClientHandler
import os


class UploadLicense:
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger

        web_ingress_node = next(
            node for node in self.config["nodes"] if "web_ingress" in node
        )
        self.web_ingress_public_ip = web_ingress_node["web_ingress"]["public_ip"]
        self.web_ingress_private_ip = web_ingress_node["private_ip"]
        self.web_ingress_ssh_username = web_ingress_node["web_ingress"]["ssh_username"]

        self.node_ssh_username = self.config["ssh_username"]

        self.ssh_client_handler = SSHClientHandler(
            self.node_ssh_username,
            self.web_ingress_ssh_username,
            self.web_ingress_public_ip,
            web_ingress_private_ip=self.web_ingress_private_ip,
            logger=logger,
        )

        self.shared_dir = next(
            node for node in self.config["nodes"] if "shared_file_system" in node
        )["shared_file_system"]["shared_dir"]

    def transfer_files(self):
        license_path = self.config["security"]["license_path"]
        airgapped_license_path = self.config["security"].get(
            "airgapped_license_path", None
        )

        # Transfer primary license file
        self.ssh_client_handler.copy_file(
            local_path=license_path,
            remote_path=os.path.join(
                self.shared_dir, "license/ndb_enterprise_license.json"
            ),
            ip=self.web_ingress_public_ip,
            username=self.web_ingress_ssh_username,
            direction="put",
        )

        # Transfer airgapped license if it exists
        if airgapped_license_path:
            self.ssh_client_handler.copy_file(
                local_path=airgapped_license_path,
                remote_path=os.path.join(self.shared_dir, "license"),
                ip=self.web_ingress_public_ip,
                username=self.web_ingress_ssh_username,
                direction="put",
            )

    def set_permissions(self):
        command = (
            f"sudo chmod g+rw {self.shared_dir}/license/ndb_enterprise_license.json"
        )
        self.ssh_client_handler.execute_commands([command], self.web_ingress_public_ip)
