import json
import paramiko


class NFSSetupManager:
    def __init__(self, config, key_path, logger):
        self.key_path = key_path
        self.config = config
        self.logger = logger

        nodes = self.config["nodes"]
        self.node_ssh_username = self.config["ssh_username"]

        shared_node = next(node for node in nodes if "shared_file_system" in node)
        web_ingress_node = next(node for node in nodes if "web_ingress" in node)

        self.shared_file_system_private_ip = shared_node["private_ip"]

        self.web_ingress_public_ip = web_ingress_node["web_ingress"]["public_ip"]
        self.web_ingress_private_ip = web_ingress_node["private_ip"]
        self.web_ingress_ssh_username = web_ingress_node["web_ingress"]["ssh_username"]

        self.shared_dir = shared_node["shared_file_system"]["shared_dir"]

        self.nfs_client_private_ips = [
            node["private_ip"]
            for node in self.config["nodes"]
            if node["private_ip"] != self.shared_ip
        ]

    def create_ssh_client(self, ip, username, proxy=None):
        try:
            sock = paramiko.ProxyCommand(proxy) if proxy else None

            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            client.connect(ip, username=username, key_filename=self.key_path, sock=sock)
            return client
        except Exception as e:
            print(f"Failed to create SSH client: {e}")
            return None

    def execute_commands(self, ssh_client, commands):
        for command in commands:
            stdin, stdout, stderr = ssh_client.exec_command(command)
            self.logger.info(f"command: {stdin.read().decode()}")
            self.logger.info(f"stdout: {stdout.read().decode()}")
            self.logger.info(f"stderr: {stderr.read().decode()}")

    def setup_shared_file_system(self):

        if self.web_ingress_private_ip == self.shared_file_system_private_ip:
            ssh_client = self.create_ssh_client(
                self.web_ingress_private_ip, self.web_ingress_ssh_username
            )
        else:
            proxy = f"ssh -o StrictHostKeyChecking=no -J {self.web_ingress_ssh_username}@{self.web_ingress_public_ip} {self.node_ssh_username}@{self.shared_file_system_private_ip}"
            ssh_client = self.create_ssh_client(
                self.shared_file_system_private_ip, self.node_ssh_username, proxy=proxy
            )

        commands = [
            "sudo apt -y update",
            "sudo groupadd -g 4646 nomad_nfs || true",
            "sudo useradd -u 4646 -g 4646 nomad_nfs || true",
            f"sudo usermod -a -G 4646 {self.ssh_username}",
            f"sudo mkdir -p {self.shared_dir}",
            f"sudo mkdir -p {self.shared_dir}/license",
            f"sudo mkdir -p {self.shared_dir}/models",
            f"sudo mkdir -p {self.shared_dir}/data",
            f"sudo mkdir -p {self.shared_dir}/users",
            f"sudo chown -R :4646 {self.shared_dir}",
            f"sudo chmod -R 774 {self.shared_dir}",
            f"sudo chmod -R g+s {self.shared_dir}",
        ]
        self.execute_commands(ssh_client, commands)

    def setup_nfs_server(self):
        if (
            "create_nfs_server" in self.config["nodes"][0]["shared_file_system"]
            and self.config["nodes"][0]["shared_file_system"]["create_nfs_server"]
        ):

            commands = [
                "sudo apt install -y nfs-kernel-server",
                "sudo apt install -y acl",
                f"sudo setfacl -d -R -m u::rwx,g::rwx,o::r {self.shared_dir}",
            ]
            if self.web_ingress_private_ip == self.shared_file_system_private_ip:
                ssh_client = self.create_ssh_client(
                    self.web_ingress_private_ip, self.web_ingress_ssh_username
                )
            else:
                proxy = f"ssh -o StrictHostKeyChecking=no -J {self.web_ingress_ssh_username}@{self.web_ingress_public_ip} {self.node_ssh_username}@{self.shared_file_system_private_ip}"
                ssh_client = self.create_ssh_client(
                    self.shared_file_system_private_ip,
                    self.node_ssh_username,
                    proxy=proxy,
                )
            self.execute_commands(ssh_client, commands)

            for ip in self.nfs_client_private_ips:
                export_line = f"{self.shared_dir} {ip}(rw,sync,no_subtree_check,all_squash,anonuid=4646,anongid=4646)"
                check_export = f'grep -qF -- "{export_line}" /etc/exports || echo "{export_line}" | sudo tee -a /etc/exports'
                self.execute_commands(ssh_client, [check_export])

            final_commands = [
                "sudo exportfs -ra",
                "if sudo systemctl is-active --quiet nfs-kernel-server; then sudo systemctl restart nfs-kernel-server; else sudo systemctl start nfs-kernel-server; fi",
                "sudo systemctl enable nfs-kernel-server",
            ]
            self.execute_commands(ssh_client, final_commands)

    def mount_nfs_clients(self):
        for client_ip in self.nfs_client_private_ips:
            if client_ip == self.web_ingress_private_ip:
                ssh_host = self.web_ingress_public_ip
                ssh_username = self.web_ingress_ssh_username
                proxy = None
            else:
                ssh_host = client_ip
                ssh_username = self.config["ssh_username"]
                proxy = f"ssh -o StrictHostKeyChecking=no -J {self.web_ingress_ssh_username}@{self.web_ingress_public_ip} {ssh_username}@{client_ip}"

            ssh_client = self.create_ssh_client(
                ssh_host,
                ssh_username,
                proxy=proxy,
            )

            commands = [
                "sudo apt -y update",
                "sudo apt-get install -y nfs-common",
                f'if [ ! -d "{self.shared_dir}" ]; then echo "Creating shared directory: {self.shared_dir}"; sudo mkdir -p "{self.shared_dir}"; fi',
                f"sudo mount -t nfs {self.shared_ip}:{self.shared_dir} {self.shared_dir}",
                f'export_line="{self.shared_ip}:{self.shared_dir} {self.shared_dir} nfs rw,hard,intr 0 0"',
                f'grep -qF -- "$export_line" /etc/fstab || echo "$export_line" | sudo tee -a /etc/fstab',
            ]

            self.execute_commands(ssh_client, commands)
