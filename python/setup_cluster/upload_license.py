from ssh_client_handler import SSHClientHandler
import os


class UploadLicense:
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger

        web_ingress_node = next(
            node for node in self.config["nodes"] if "web_ingress" in node
        )
        self.web_ingress_public_ip = web_ingress_node["web_ingress"]["public_ip"]
        self.web_ingress_ssh_username = web_ingress_node["web_ingress"]["ssh_username"]

        self.node_ssh_username = self.config["ssh_username"]

        self.ssh_client_handler = SSHClientHandler(
            self.node_ssh_username,
            self.web_ingress_ssh_username,
            self.web_ingress_public_ip,
            logger=logger,
        )

    def transfer_files(self):
        """Transfer license files to the web ingress node."""
        shared_dir = next(
            node for node in self.config["nodes"] if "shared_file_system" in node
        )["shared_file_system"]["shared_dir"]
        license_path = self.config["security"]["license_path"]
        airgapped_license_path = self.config["security"].get(
            "airgapped_license_path", None
        )

        # Transfer primary license file
        self.ssh_client_handler.copy_file(
            license_path,
            f"{shared_dir}/license",
            self.web_ingress_public_ip,
            self.web_ingress_ssh_username,
        )

        # Transfer airgapped license if it exists
        if airgapped_license_path:
            self.ssh_client_handler.copy_file(
                airgapped_license_path,
                f"{shared_dir}/license",
                self.web_ingress_public_ip,
                self.web_ingress_ssh_username,
            )

    def set_permissions(self):
        """Set permissions on the remote directory."""
        shared_dir = next(
            node for node in self.config["nodes"] if "shared_file_system" in node
        )["shared_file_system"]["shared_dir"]
        command = f"sudo chmod g+rw {shared_dir}/license/ndb_enterprise_license.json"
        self.ssh_client_handler.execute_command([command], self.web_ingress_public_ip)
