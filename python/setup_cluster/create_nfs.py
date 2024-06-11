import json
import paramiko


class NFSSetupManager:
    def __init__(self, config, key_path):
        # TODO(pratik): Assume id_rsa is the key
        self.key_path = key_path
        self.config = config
        self.ssh_client = None

    def create_ssh_client(self, ip, username):
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(ip, username=username, key_filename=self.key_path)
        return client

    def execute_commands(self, commands):
        for command in commands:
            stdin, stdout, stderr = self.ssh_client.exec_command(command)
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
            self.ssh_client = self.create_ssh_client(web_ip, web_ssh_username)
        else:
            self.ssh_client = self.create_ssh_client(shared_ip, ssh_username)

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
        self.execute_commands(commands)

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
            self.execute_commands(commands)

            exports_config = ""
            for ip in nfs_client_private_ips:
                export_line = f"{shared_dir} {ip}(rw,sync,no_subtree_check,all_squash,anonuid=4646,anongid=4646)"
                exports_config += f'echo "{export_line}" | sudo tee -a /etc/exports\n'
            exports_config += "sudo exportfs -ra\n"
            exports_config += "sudo systemctl restart nfs-kernel-server || sudo systemctl start nfs-kernel-server\n"
            exports_config += "sudo systemctl enable nfs-kernel-server\n"

            self.execute_commands([exports_config])

    def close(self):
        if self.ssh_client:
            self.ssh_client.close()
