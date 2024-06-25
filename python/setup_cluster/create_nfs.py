from setup_cluster.ssh_client_handler import SSHClientHandler


class NFSSetupManager:
    def __init__(self, config, logger):
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
            if node["private_ip"] != self.shared_file_system_private_ip
        ]
        self.ssh_client_handler = SSHClientHandler(
            self.node_ssh_username,
            self.web_ingress_ssh_username,
            self.web_ingress_public_ip,
            self.web_ingress_private_ip,
            logger=logger,
        )

    def setup_shared_file_system(self):
        commands = [
            "sudo apt -y update",
            "sudo groupadd -g 4646 nomad_nfs || true",
            "sudo useradd -u 4646 -g 4646 nomad_nfs || true",
            f"sudo usermod -a -G 4646 {self.node_ssh_username}",
            f"sudo mkdir -p {self.shared_dir}",
            f"sudo mkdir -p {self.shared_dir}/license",
            f"sudo mkdir -p {self.shared_dir}/models",
            f"sudo mkdir -p {self.shared_dir}/data",
            f"sudo mkdir -p {self.shared_dir}/users",
            f"sudo chown -R :4646 {self.shared_dir}",
            f"sudo chmod -R 774 {self.shared_dir}",
            f"sudo chmod -R g+s {self.shared_dir}",
            "sudo apt install -y nfs-kernel-server",
            "sudo apt install -y acl",
            f"sudo setfacl -d -R -m u::rwx,g::rwx,o::r {self.shared_dir}",
        ]

        use_proxy = self.web_ingress_private_ip != self.shared_file_system_private_ip
        self.ssh_client_handler.execute_commands(
            commands,
            (
                self.shared_file_system_private_ip
                if use_proxy
                else self.web_ingress_public_ip
            ),
            use_proxy,
        )

    def setup_nfs_server(self):
        if (
            "create_nfs_server" in self.config["nodes"][0]["shared_file_system"]
            and self.config["nodes"][0]["shared_file_system"]["create_nfs_server"]
        ):

            use_proxy = (
                self.web_ingress_private_ip != self.shared_file_system_private_ip
            )

            for ip in self.nfs_client_private_ips:
                export_line = f"{self.shared_dir} {ip}(rw,sync,no_subtree_check,all_squash,anonuid=4646,anongid=4646)"
                check_export = f'grep -qF -- "{export_line}" /etc/exports || echo "{export_line}" | sudo tee -a /etc/exports'
                self.ssh_client_handler.execute_commands(
                    [check_export],
                    (
                        self.shared_file_system_private_ip
                        if use_proxy
                        else self.web_ingress_public_ip
                    ),
                    use_proxy,
                )

            final_commands = [
                "sudo exportfs -ra",
                "if sudo systemctl is-active --quiet nfs-kernel-server; then sudo systemctl restart nfs-kernel-server; else sudo systemctl start nfs-kernel-server; fi",
                "sudo systemctl enable nfs-kernel-server",
            ]
            self.ssh_client_handler.execute_commands(
                final_commands,
                (
                    self.shared_file_system_private_ip
                    if use_proxy
                    else self.web_ingress_public_ip
                ),
                use_proxy,
            )

    def mount_nfs_clients(self):
        commands = [
            "sudo apt -y update",
            "sudo apt-get install -y nfs-common",
            f'if [ ! -d "{self.shared_dir}" ]; then echo "Creating shared directory: {self.shared_dir}"; sudo mkdir -p "{self.shared_dir}"; fi',
            f"sudo mount -t nfs {self.shared_file_system_private_ip}:{self.shared_dir} {self.shared_dir}",
            f'export_line="{self.shared_file_system_private_ip}:{self.shared_dir} {self.shared_dir} nfs rw,hard,intr 0 0"',
            f'grep -qF -- "$export_line" /etc/fstab || echo "$export_line" | sudo tee -a /etc/fstab',
        ]
        for client_ip in self.nfs_client_private_ips:
            self.ssh_client_handler.execute_commands(
                commands,
                client_ip,
                (self.web_ingress_private_ip != client_ip),
            )
