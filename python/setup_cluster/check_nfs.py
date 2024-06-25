import paramiko
import json
from setup_cluster.ssh_client_handler import SSHClientHandler
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

    def write_status_on_nfs(self):
        """
        Writes the status of each node to a status file on a Network File System (NFS).

        Returns:
            list: A list of results from executing the SSH commands on each node.
        """
        
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

    def verify_status_on_nodes(self):
        """
        Verify the NFS status on each node.

        Returns:
            tuple: A tuple containing a list of results from each node and a boolean indicating the 
                overall status (True if all nodes are successful, False otherwise).
        """
    
        results = []
        check_command_template = "grep -q '{ip} | success' {file_location} && echo '{ip} | success' || echo '{ip} | failed'"
        status = True
        for node in self.nodes:
            ip = node["private_ip"]
            check_command = check_command_template.format(
                ip=ip, file_location=self.status_file_loc
            )

            result = self.ssh_client_handler.execute_commands(
                [check_command], self.web_ingress_public_ip, False
            )
            results.append(result)
            if "success" in result:
                self.logger.info(f"NFS verification success for IP {ip}.")
            else:
                self.logger.error(f"NFS verification failed for IP {ip}.")
                status = False

        return results, status

    def clean_up(self):
        """
        Cleans up by removing the status file on the server.

        Returns:
            bool: True if the cleanup was successful, False if there was an error.
        """
        try:
            self.ssh_client_handler.execute_commands(
                [f"sudo rm -f {self.status_file_loc}"], self.web_ingress_public_ip
            )
            return True
        except Exception as e:
            self.logger.error(f"Error cleaning up file: {e}")
            return False
