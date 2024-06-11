import paramiko
from paramiko import SSHClient
import json


class NodeStatusChecker:
    def __init__(self, config):
        self.config = config
        self.ssh_client = SSHClient()
        self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.nodes = config["nodes"]
        self.web_ingress_node = next(
            node for node in self.nodes if "web_ingress" in node
        )
        self.node_ssh_username = config["ssh_username"]
        self.web_ingress_ssh_username = self.web_ingress_node["web_ingress"][
            "ssh_username"
        ]
        self.web_ingress_public_ip = self.web_ingress_node["web_ingress"]["public_ip"]
        self.web_ingress_private_ip = self.web_ingress_node["private_ip"]
        self.shared_dir = next(
            node for node in self.nodes if "shared_file_system" in node
        )["shared_file_system"]["shared_dir"]
        self.status_file_loc = f"{self.shared_dir}/node_status"

    def connect_ssh(self, ip, username):
        self.ssh_client.connect(
            ip, username=username, key_filename="path_to_private_key.pem"
        )

    def execute_command(self, command, ip, use_jump=False):
        if use_jump:
            proxy = paramiko.ProxyCommand(
                f"ssh -q -W %h:%p {self.web_ingress_ssh_username}@{self.web_ingress_public_ip}"
            )
            self.ssh_client.connect(ip, username=self.node_ssh_username, sock=proxy)
        else:
            self.connect_ssh(ip, self.node_ssh_username)

        stdin, stdout, stderr = self.ssh_client.exec_command(command)
        result = stdout.read().decode().strip()
        error = stderr.read().decode().strip()
        if error:
            print("Error:", error)
        return result

    def check_status_on_nodes(self):
        node_private_ips = [node["private_ip"] for node in self.nodes]
        results = []
        for ip in node_private_ips:
            command = f'echo "{ip} | success" | sudo tee -a {self.status_file_loc}'
            use_jump = ip != self.web_ingress_private_ip
            result = self.execute_command(command, ip, use_jump)
            results.append(result)

        return results

    def copy_status_file(self):
        local_path = "./node_status"
        remote_path = f"{self.web_ingress_ssh_username}@{self.web_ingress_public_ip}:{self.status_file_loc}"
        with paramiko.SFTPClient.from_transport(
            self.ssh_client.get_transport()
        ) as sftp:
            sftp.get(remote_path, local_path)

        with open(local_path, "r") as f:
            lines = f.readlines()

        if len(lines) != len(self.nodes):
            print("Shared directory is not accessible by every node")
            return False
        else:
            print("Shared directory is accessible by every node")
            return True

    def clean_up(self):
        self.execute_command(
            f"sudo rm -f {self.status_file_loc}", self.web_ingress_private_ip
        )
        self.ssh_client.close()
