import paramiko
import json
from ssh_client_handler import SSHClientHandler
import os


class NodeStatusChecker:
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
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
        self.status_file_loc = os.path.join(self.shared_dir, "node_status")

        self.ssh_client_handler = SSHClientHandler(
            self.node_ssh_username,
            self.web_ingress_ssh_username,
            self.web_ingress_public_ip,
            web_ingress_private_ip=self.web_ingress_private_ip,
            logger=logger,
        )

    def check_status_on_nodes(self):
        results = []
        for node in self.nodes:
            ip = node["private_ip"]
            command = f'echo "{ip} | success" | sudo tee -a {self.status_file_loc}'
            use_jump = ip != self.web_ingress_private_ip
            if ip == self.web_ingress_private_ip:
                ip = self.web_ingress_public_ip
            result = self.ssh_client_handler.execute_commands([command], ip, use_jump)
            results.append(result)
        return results

    def copy_status_file(self):
        # TODO(pratik): Write a test matching each of the ip written
        local_path = "./node_status"
        self.ssh_client_handler.copy_file(
            local_path,
            self.status_file_loc,
            self.web_ingress_public_ip,
            self.web_ingress_ssh_username,
            "get",
        )

    def clean_up(self):
        try:
            self.ssh_client_handler.execute_commands(
                [f"sudo rm -f {self.status_file_loc}"], self.web_ingress_public_ip
            )
            return True
        except Exception as e:
            self.logger.error(f"Error cleaning up file: {e}")
            return False
