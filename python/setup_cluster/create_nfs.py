import json
import paramiko


class NFSSetupManager:
    def __init__(self, config, key_path):
        self.key_path = key_path
        self.config = config

    def create_ssh_client(self, ip, username, proxy=None):
        if proxy:
            proxy = paramiko.ProxyCommand(proxy)
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(ip, username=username, key_filename=self.key_path, sock=proxy)
        return client

    def execute_commands(self, ssh_client, commands):
        for command in commands:
            stdin, stdout, stderr = ssh_client.exec_command(command)
            print(stdout.read().decode())
            print(stderr.read().decode())

    def setup_shared_file_system(self):
        nodes = self.config["nodes"]
        ssh_username = self.config["ssh_username"]
        shared_node = next(node for node in nodes if "shared_file_system" in node)
        web_ingress_node = next(node for node in nodes if "web_ingress" in node)

        shared_ip = shared_node["private_ip"]
        web_ip = web_ingress_node["web_ingress"]["public_ip"]
        web_private_ip = web_ingress_node["private_ip"]
        web_ssh_username = web_ingress_node["web_ingress"]["ssh_username"]
        shared_dir = shared_node["shared_file_system"]["shared_dir"]

        if web_private_ip == shared_ip:
            ssh_client = self.create_ssh_client(web_ip, web_ssh_username)
        else:
            ssh_client = self.create_ssh_client(shared_ip, ssh_username)

        commands = [
            "sudo apt -y update",
            "sudo groupadd -g 4646 nomad_nfs || true",
            "sudo useradd -u 4646 -g 4646 nomad_nfs || true",
            f"sudo usermod -a -G 4646 {ssh_username}",
            f"sudo mkdir -p {shared_dir}",
            f"sudo mkdir -p {shared_dir}/license",
            f"sudo mkdir -p {shared_dir}/models",
            f"sudo mkdir -p {shared_dir}/data",
            f"sudo mkdir -p {shared_dir}/users",
            f"sudo chown -R :4646 {shared_dir}",
            f"sudo chmod -R 774 {shared_dir}",
            f"sudo chmod -R g+s {shared_dir}",
        ]
        self.execute_commands(ssh_client, commands)

    def setup_nfs_server(self):
        if (
            "create_nfs_server" in self.config["nodes"][0]["shared_file_system"]
            and self.config["nodes"][0]["shared_file_system"]["create_nfs_server"]
        ):
            shared_ip = self.config["nodes"][0]["private_ip"]
            shared_dir = self.config["nodes"][0]["shared_file_system"]["shared_dir"]
            nfs_client_private_ips = [
                node["private_ip"]
                for node in self.config["nodes"]
                if node["private_ip"] != shared_ip
            ]

            commands = [
                "sudo apt install -y nfs-kernel-server",
                "sudo apt install -y acl",
                f"sudo setfacl -d -R -m u::rwx,g::rwx,o::r {shared_dir}",
            ]
            ssh_client = self.create_ssh_client(
                shared_ip,
            )
            self.execute_commands(commands)

            for ip in nfs_client_private_ips:
                export_line = f"{shared_dir} {ip}(rw,sync,no_subtree_check,all_squash,anonuid=4646,anongid=4646)"
                check_export = f'grep -qF -- "{export_line}" /etc/exports || echo "{export_line}" | sudo tee -a /etc/exports'
                self.execute_commands(
                    [check_export], shared_ip, self.config["ssh_username"]
                )

            final_commands = [
                "sudo exportfs -ra",
                "if sudo systemctl is-active --quiet nfs-kernel-server; then sudo systemctl restart nfs-kernel-server; else sudo systemctl start nfs-kernel-server; fi",
                "sudo systemctl enable nfs-kernel-server",
            ]
            self.execute_commands(
                final_commands, shared_ip, self.config["ssh_username"]
            )

    def mount_nfs_clients(self):
        shared_ip = self.config["nodes"][0]["private_ip"]
        shared_dir = self.config["nodes"][0]["shared_file_system"]["shared_dir"]
        nfs_client_private_ips = [
            node["private_ip"]
            for node in self.config["nodes"]
            if node["private_ip"] != shared_ip
        ]

        for client_ip in nfs_client_private_ips:
            if client_ip == self.config["nodes"][0]["private_ip"]:
                ssh_host = self.config["web_ingress"]["public_ip"]
                ssh_username = self.config["web_ingress"]["ssh_username"]
                proxy = None
            else:
                ssh_host = client_ip
                ssh_username = self.config["ssh_username"]
                proxy = f"ssh -o StrictHostKeyChecking=no -J {self.config['web_ingress']['ssh_username']}@{self.config['web_ingress']['public_ip']} {self.config['ssh_username']}@{client_ip}"

            commands = [
                "sudo apt -y update",
                "sudo apt-get install -y nfs-common",
                f'if [ ! -d "{shared_dir}" ]; then echo "Creating shared directory: {shared_dir}"; sudo mkdir -p "{shared_dir}"; fi',
                f"sudo mount -t nfs {shared_ip}:{shared_dir} {shared_dir}",
                f'export_line="{shared_ip}:{shared_dir} {shared_dir} nfs rw,hard,intr 0 0"',
                f'grep -qF -- "$export_line" /etc/fstab || echo "$export_line" | sudo tee -a /etc/fstab',
            ]
            self.execute_commands(commands, ssh_host, ssh_username)

    def close(self):
        if self.ssh_client:
            self.ssh_client.close()
