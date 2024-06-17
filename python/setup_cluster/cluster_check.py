import logging


class ClusterValidator:
    def __init__(self, config, logger=None):
        self.config = config
        self.nodes = config["nodes"]
        if logger is None:
            logger = logging.getLogger(__name__)
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.DEBUG)
        self.logger = logger
        self.ssh_handler = SSHClientHandler(
            node_ssh_username=config["ssh_username"],
            web_ingress_ssh_username=config["nodes"][0]["web_ingress"]["ssh_username"],
            web_ingress_public_ip=config["nodes"][0]["web_ingress"]["public_ip"],
            web_ingress_private_ip=config["nodes"][0]["private_ip"],
            logger=self.logger,
        )

    def has_public_ip(self):
        return any("web_ingress" in node for node in self.nodes)

    def check_ssh_and_sudo_access(self, node_ip):
        commands = ["sudo -n echo Sudo check passed"]
        result = self.ssh_handler.execute_commands(
            commands, node_ip, use_jump=True, run_sequenctially=True
        )
        return "Sudo check passed" in result if result else False

    def check_internet_access(self, node_ip):
        commands = ["ping -c 3 www.google.com"]
        result = self.ssh_handler.execute_commands(commands, node_ip, use_jump=True)
        return "0% packet loss" in result

    def check_system_resources(self, node_ip):
        commands = ["cat /proc/meminfo | grep MemTotal", "nproc"]
        result = self.ssh_handler.execute_commands(
            commands, node_ip, use_jump=True, run_sequenctially=True
        )
        if result:
            mem_total = int(result.split()[1]) / 1024**2  # Convert kB to GB
            cpu_count = int(result.split()[-1])
            return mem_total >= 8 and cpu_count >= 1
        return False

    def check_ubuntu_version(self, node_ip):
        commands = ["lsb_release -a"]
        result = self.ssh_handler.execute_commands(commands, node_ip, use_jump=True)
        return "Ubuntu 22.04" in result

    def has_public_ip(self):
        return any("web_ingress" in node for node in self.nodes)

    def check_port_exposure(self, node_ip, ports):
        results = {}
        for port in ports:
            commands = [f"nc -zv {node_ip} {port}"]
            output = self.ssh_handler.execute_commands(commands, node_ip, use_jump=True)
            results[port] = "succeeded" in output if output else False
            if not results[port]:
                self.logger.warning(
                    f"Port {port} is not exposed on {node_ip}. Follow the firewall setup instructions."
                )
        return results

    def validate_cluster(self):
        if not self.has_public_ip():
            self.logger.error("No public IP found in any node.")
            return False

        results = {}
        ports_to_check = [
            22,
            80,
            443,
            4646,
            5432,
        ]
        for node in self.nodes:
            node_ip = node["private_ip"]
            results[node_ip] = {
                "SSH and Sudo Access": self.check_ssh_and_sudo_access(node_ip),
                "Internet Access": self.check_internet_access(node_ip),
                "System Resources": self.check_system_resources(node_ip),
                "Ubuntu Version": self.check_ubuntu_version(node_ip),
                "Port Accessibility": self.check_port_exposure(node_ip, ports_to_check),
            }

        return results
