import paramiko


class NomadDeployer:
    def __init__(self, config):
        self.config = config
        self.repo_url = "https://github.com/ThirdAILabs/neuraldb-enterprise.git"
        self.repo_dir = "neuraldb-enterprise"
        self.initialize_ssh_client()

    def initialize_ssh_client(self):
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    def ssh_command(self, host, username, commands, proxy=None):
        if proxy:
            proxy = paramiko.ProxyCommand(proxy)
            self.ssh.connect(hostname=host, username=username, sock=proxy)
        else:
            self.ssh.connect(hostname=host, username=username)

        for command in commands:
            stdin, stdout, stderr = self.ssh.exec_command(command)
            print(stdout.read().decode())
            print(stderr.read().decode())

        self.ssh.close()

    def deploy(self):
        node_private_ips = [node["private_ip"] for node in self.config["nodes"]]
        web_ingress = next(
            node for node in self.config["nodes"] if "web_ingress" in node
        )
        web_ingress_private_ip = web_ingress["private_ip"]
        web_ingress_public_ip = web_ingress["web_ingress"]["public_ip"]
        node_ssh_username = self.config["ssh_username"]
        web_ingress_ssh_username = web_ingress["web_ingress"]["ssh_username"]

        install_commands = self.get_install_commands()

        for ip in node_private_ips:
            if ip == web_ingress_private_ip:
                self.ssh_command(
                    web_ingress_public_ip, web_ingress_ssh_username, install_commands
                )
            else:
                proxy_cmd = f"ssh -o StrictHostKeyChecking=no -J {web_ingress_ssh_username}@{web_ingress_public_ip} {node_ssh_username}@{ip}"
                self.ssh_command(
                    ip, node_ssh_username, install_commands, proxy=proxy_cmd
                )

    def get_install_commands(self):
        return [
            "sudo apt update",
            "command -v wget >/dev/null || (echo 'wget not found. Installing...' && sudo apt install -y wget)",
            "command -v docker >/dev/null || (wget -O get-docker.sh https://get.docker.com/ && bash get-docker.sh && docker run hello-world)",
            "command -v tmux >/dev/null || (echo 'tmux not found. Installing...' && sudo apt install -y tmux)",
            "if [ -f '/usr/share/keyrings/hashicorp-archive-keyring.gpg' ]; then sudo rm '/usr/share/keyrings/hashicorp-archive-keyring.gpg'; fi",
            "wget -O- https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o '/usr/share/keyrings/hashicorp-archive-keyring.gpg'",
            "echo 'deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main' | sudo tee /etc/apt/sources.list.d/hashicorp.list",
            "sudo apt-get update && sudo apt-get install -y nomad='1.6.2-1'",
            "rm -rf '{}' && git clone -b acl '{}' && cd '{}'".format(
                self.repo_dir, self.repo_url, self.repo_dir
            ),
        ]

    def bootstrap_acl(self):
        nomad_server_ip = next(
            node["private_ip"]
            for node in self.config["nodes"]
            if "nomad_server" in node
        )
        node_ssh_username = self.config["ssh_username"]
        nomad_data_dir = "/opt/neuraldb_enterprise/nomad_data"

        acl_commands = [
            f"sudo mkdir -p {nomad_data_dir}",
            f"if [ ! -f '{nomad_data_dir}/management_token.txt' ]; then sudo bash -c 'nomad acl bootstrap > {nomad_data_dir}/management_token.txt 2>&1'; fi",
            "management_token=$(grep 'Secret ID' {}/management_token.txt | awk '{{print $NF}}')".format(
                nomad_data_dir
            ),
            f"cd {self.repo_dir}",
            "nomad acl policy apply -description 'Task Runner policy' -token $management_token task-runner './nomad/nomad_node_configs/task_runner.policy.hcl'",
            f"nomad acl token create -name='Task Runner token' -policy=task-runner -type=client -token $management_token 2>&1 | sudo tee {nomad_data_dir}/task_runner_token.txt > /dev/null",
            "task_runner_token=$(grep 'Secret ID' {}/task_runner_token.txt | awk '{{print $NF}}')".format(
                nomad_data_dir
            ),
            "nomad var put -namespace default -token $management_token -force nomad/jobs task_runner_token=$task_runner_token > /dev/null",
        ]
        self.ssh_command(nomad_server_ip, node_ssh_username, acl_commands)

    def start_nomad_clients(self):
        nomad_server_ip = next(
            node["private_ip"]
            for node in self.config["nodes"]
            if "nomad_server" in node
        )
        nomad_client_private_ips = [
            node["private_ip"]
            for node in self.config["nodes"]
            if node["private_ip"] != nomad_server_ip
        ]
        web_ingress = next(
            node for node in self.config["nodes"] if "web_ingress" in node
        )
        web_ingress_private_ip = web_ingress["private_ip"]
        web_ingress_public_ip = web_ingress["web_ingress"]["public_ip"]
        node_ssh_username = self.config["ssh_username"]
        web_ingress_ssh_username = web_ingress["web_ingress"]["ssh_username"]

        for ip in nomad_client_private_ips:
            node_pool = (
                "default"
                if self.config["nodes"][0].get("web_ingress", {}).get("run_jobs", True)
                else "web_ingress"
            )
            node_class = "web_ingress" if ip == web_ingress_private_ip else "default"
            if ip == web_ingress_private_ip:
                ssh_host = web_ingress_public_ip
                ssh_username = web_ingress_ssh_username
                proxy = None
            else:
                ssh_host = ip
                ssh_username = node_ssh_username
                proxy = f"ssh -o StrictHostKeyChecking=no -J {web_ingress_ssh_username}@{web_ingress_public_ip} {node_ssh_username}@{ip}"

            client_commands = [
                "tmux has-session -t nomad-agent 2>/dev/null && tmux kill-session -t nomad-agent",
                f"tmux new-session -d -s nomad-agent 'cd {self.repo_dir}; bash ./nomad/nomad_scripts/start_nomad_agent.sh false true {node_pool} {node_class} {nomad_server_ip} {ip} > head.log 2> head.err'",
            ]
            self.ssh_command(ssh_host, ssh_username, client_commands, proxy)

    def close_ssh_connection(self):
        """Close the SSH connection if it is open."""
        try:
            if self.ssh.get_transport() and self.ssh.get_transport().is_active():
                self.ssh.close()
        except Exception as e:
            print(f"Failed to close SSH connection: {e}")
