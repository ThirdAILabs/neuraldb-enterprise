import warnings
from setup_cluster.ssh_client_handler import SSHClientHandler


class ClusterValidator:
    def __init__(self, config, logger):
        self.config = config
        self.nodes = config["nodes"]
        self.logger = logger
        self.ssh_handler = SSHClientHandler(
            node_ssh_username=config["ssh_username"],
            web_ingress_ssh_username=config["nodes"][0]["web_ingress"]["ssh_username"],
            web_ingress_public_ip=config["nodes"][0]["web_ingress"]["public_ip"],
            web_ingress_private_ip=config["nodes"][0]["private_ip"],
            logger=self.logger,
        )

    def has_public_ip(self):
        has_ip = any("web_ingress" in node for node in self.nodes)
        if not has_ip:
            error_message = "Validation failed: No nodes have a public IP."
            self.logger.error(error_message)
            return False
        else:
            self.logger.info("Validation successful: All nodes have a public IP.")
            return True

    def check_ssh_and_sudo_access(self, node_ip, use_jump=True):
        commands = ["sudo -n echo Sudo check passed"]
        result = self.ssh_handler.execute_commands(
            commands, node_ip, use_jump=use_jump, run_sequentially=True
        )
        if not result:
            error_message = (
                f"Passwordless SSH or sudo access not configured properly on {node_ip}."
            )
            self.logger.error(error_message)
            return False
        if "Sudo check passed" in result:
            self.logger.info(f"SSH and sudo access confirmed for {node_ip}.")
            return True
        else:
            error_message = (
                f"Passwordless SSH or sudo access not configured properly on {node_ip}."
            )
            self.logger.error(error_message)
            return False

    def check_internet_access(self, node_ip, use_jump=True):
        commands = ["ping -c 3 www.google.com"]
        result = self.ssh_handler.execute_commands(commands, node_ip, use_jump=use_jump)
        if not result:
            error_message = f"No internet access on {node_ip}."
            self.logger.error(error_message)
            return False
        if "0% packet loss" in result:
            self.logger.info(f"Internet access verified for {node_ip}.")
            return True
        else:
            error_message = f"No internet access on {node_ip}."
            self.logger.error(error_message)
            return False

    def check_system_resources(self, node_ip, use_jump=True):
        commands = ["cat /proc/meminfo | grep MemTotal", "nproc"]
        result = self.ssh_handler.execute_commands(
            commands, node_ip, use_jump=use_jump, run_sequentially=True
        )
        if not result:
            error_message = f"Failed to retrieve system resources for {node_ip}."
            self.logger.warning(error_message)
            return False
        mem_total = int(result.split()[1]) / 1024**2  # Convert kB to GB
        cpu_count = int(result.split()[-1])
        if mem_total >= 8 and cpu_count >= 1:
            self.logger.info(f"System resources meet requirements for {node_ip}.")
            return True
        else:
            error_message = f"Insufficient system resources on {node_ip}. Nodes should have at least 8GB of RAM and 1 CPU."
            self.logger.error(error_message)
            return False

    def check_ubuntu_version(self, node_ip, use_jump=True):
        commands = ["lsb_release -a"]
        result = self.ssh_handler.execute_commands(commands, node_ip, use_jump=use_jump)
        if not result:
            error_message = f"Failed to retrieve Ubuntu version for {node_ip}."
            self.logger.warning(error_message)
            return False
        if "Ubuntu 22.04" in result:
            self.logger.info(f"Ubuntu version confirmed on {node_ip}.")
            return True
        else:
            error_message = f"Incorrect Ubuntu version on {node_ip}. Need Ubuntu 22.04."
            self.logger.error(error_message)
            return False

    def check_port_exposure(self, node_ip, ports, use_jump=True):
        passed = True
        for port in ports:
            commands = [f"nc -zv {node_ip} {port}"]
            output = self.ssh_handler.execute_commands(
                commands, node_ip, use_jump=use_jump, expect_stderr=True
            )
            if "succeeded" in output:
                error_message = f"Port {port} is in use on {node_ip}."
                self.logger.error(error_message)
                passed = False
        return passed

    def validate_cluster(self):
        if not self.has_public_ip():
            return False

        results = {}
        ports_to_check = [22, 80, 443, 2049, 4646, 5432]
        for node in self.nodes:
            node_ip = node["private_ip"]
            if "web_ingress" in node:
                node_ip = self.nodes[0]["web_ingress"]["public_ip"]
                results[node_ip] = {
                    "SSH and Sudo Access": self.check_ssh_and_sudo_access(
                        node_ip, False
                    ),
                    "Internet Access": self.check_internet_access(node_ip, False),
                    "System Resources": self.check_system_resources(node_ip, False),
                    "Ubuntu Version": self.check_ubuntu_version(node_ip, False),
                    "Port Accessibility": self.check_port_exposure(
                        node_ip, ports_to_check, False
                    ),
                }
            else:
                results[node_ip] = {
                    "SSH and Sudo Access": self.check_ssh_and_sudo_access(node_ip),
                    "Internet Access": self.check_internet_access(node_ip),
                    "System Resources": self.check_system_resources(node_ip),
                    "Ubuntu Version": self.check_ubuntu_version(node_ip),
                    "Port Accessibility": self.check_port_exposure(
                        node_ip, ports_to_check
                    ),
                }

        return results
