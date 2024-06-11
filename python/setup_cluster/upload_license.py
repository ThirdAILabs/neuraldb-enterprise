import paramiko
import os


class NeuralDBClusterSetup:
    def __init__(self, config):
        self.config = config
        self.ssh_client = paramiko.SSHClient()
        self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.setup_ssh_connection()

    def setup_ssh_connection(self):
        """Establish SSH connection using the provided configuration."""
        web_ingress_node = next(
            node for node in self.config["nodes"] if "web_ingress" in node
        )
        self.web_ingress_public_ip = web_ingress_node["web_ingress"]["public_ip"]
        self.web_ingress_ssh_username = web_ingress_node["web_ingress"]["ssh_username"]
        key_path = os.path.expanduser(
            self.config["ssh"]["public_key_path"].replace(".pub", "")
        )  # Private key assumed
        self.ssh_client.connect(
            self.web_ingress_public_ip,
            username=self.web_ingress_ssh_username,
            key_filename=key_path,
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
        self.transfer_file(license_path, f"{shared_dir}/license")

        # Transfer airgapped license if it exists
        if airgapped_license_path:
            self.transfer_file(airgapped_license_path, f"{shared_dir}/license")

    def transfer_file(self, local_path, remote_path):
        """Helper function to transfer a single file."""
        with paramiko.SFTPClient.from_transport(
            self.ssh_client.get_transport()
        ) as sftp:
            sftp.put(local_path, f"{remote_path}/{os.path.basename(local_path)}")

    def set_permissions(self):
        """Set permissions on the remote directory."""
        shared_dir = next(
            node for node in self.config["nodes"] if "shared_file_system" in node
        )["shared_file_system"]["shared_dir"]
        command = f"sudo chmod g+rw {shared_dir}/license/ndb_enterprise_license.json"
        stdin, stdout, stderr = self.ssh_client.exec_command(command)
        print(stdout.read().decode())
        print(stderr.read().decode())

    def close(self):
        """Close the SSH connection."""
        self.ssh_client.close()
