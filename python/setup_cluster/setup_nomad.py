from ssh_client_handler import SSHClientHandler
import time


class NomadDeployer:
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger

        self.repo_url = "https://github.com/ThirdAILabs/neuraldb-enterprise.git"
        self.repo_dir = "neuraldb-enterprise"
        self.node_private_ips = [node["private_ip"] for node in self.config["nodes"]]
        web_ingress = next(
            node for node in self.config["nodes"] if "web_ingress" in node
        )
        self.web_ingress_private_ip = web_ingress["private_ip"]
        self.web_ingress_public_ip = web_ingress["web_ingress"]["public_ip"]
        self.node_ssh_username = self.config["ssh_username"]
        self.web_ingress_ssh_username = web_ingress["web_ingress"]["ssh_username"]

        self.ssh_client_handler = SSHClientHandler(
            self.node_ssh_username,
            self.web_ingress_ssh_username,
            self.web_ingress_public_ip,
            logger=logger,
        )

        self.nomad_server_private_ip = next(
            node["private_ip"]
            for node in self.config["nodes"]
            if "nomad_server" in node
        )

    def get_install_commands(self):
        return [
            "sudo apt update",
            # Install wget
            "if ! command -v wget &> /dev/null; then echo 'wget not found. Installing...' && sudo apt install -y wget; else echo 'wget is already installed.'; fi",
            # Install docker
            "if ! command -v docker &> /dev/null; then wget -O get-docker.sh https://get.docker.com/ && bash get-docker.sh && docker run hello-world; else echo 'Docker is already installed.'; fi",
            # Install tmux
            "if ! command -v tmux &> /dev/null; then echo 'tmux not found. Installing...' && sudo apt install -y tmux; else echo 'tmux is already installed.'; fi",
            # Install nomad
            "keyring_file='/usr/share/keyrings/hashicorp-archive-keyring.gpg'",
            "if [ -f $keyring_file ]; then sudo rm $keyring_file; fi",
            "wget -O- https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o $keyring_file",
            "echo 'deb [signed-by=$keyring_file] https://apt.releases.hashicorp.com $(lsb_release -cs) main' | sudo tee /etc/apt/sources.list.d/hashicorp.list",
            "sudo apt-get update && sudo apt-get install -y nomad='1.6.2-1'",
            # Cloning neuraldb-enterprise repo
            "rm -rf {} && git clone -b acl {} && cd {}".format(
                self.repo_dir, self.repo_url, self.repo_dir
            ),
        ]

    def deploy(self):

        install_commands = self.get_install_commands()

        for ip in self.node_private_ips:
            use_proxy = self.web_ingress_private_ip != ip
            self.ssh_client_handler.execute_commands(
                install_commands,
                (ip if use_proxy else self.web_ingress_public_ip),
                use_proxy,
            )

    def setup_nomad_cluster(self):
        self.logger.info("Setting up Nomad Cluster...")

        if self.web_ingress_private_ip == self.nomad_server_private_ip:
            node_class = "web_ingress"
        else:
            node_class = "default"

        self.logger.info("Starting Initial Nomad Server")
        node_pool = next(
            (
                "default"
                if node.get("web_ingress", {}).get("run_jobs", True)
                else "web_ingress"
            )
            for node in self.config["nodes"]
            if node["private_ip"] == self.nomad_server_private_ip
        )

        commands = [
            "tmux has-session -t nomad-agent 2>/dev/null && tmux kill-session -t nomad-agent",
            f"tmux new-session -d -s nomad-agent 'cd {self.repo_dir}; bash ./nomad/nomad_scripts/start_nomad_agent.sh true true {node_pool} {node_class} {self.nomad_server_private_ip} {self.nomad_server_private_ip} > head.log 2> head.err'",
        ]

        self.ssh_client_handler.execute_command(
            commands,
            self.nomad_server_private_ip,
            use_jump=(self.web_ingress_private_ip != self.nomad_server_private_ip),
        )

        # TODO(pratik): do we even need it? given we wait for ssh command to finish.
        time.sleep(20)

    def bootstrap_acl_system(self):
        self.logger.info("Bootstrapping ACL system")

        nomad_data_dir = "/opt/neuraldb_enterprise/nomad_data"
        repo_dir = self.repo_dir

        commands = [
            f"sudo mkdir -p {nomad_data_dir}",
            f"if [ ! -f '{nomad_data_dir}/management_token.txt' ]; then sudo bash -c 'nomad acl bootstrap > {nomad_data_dir}/management_token.txt 2>&1'; fi",
            f"management_token=$(grep 'Secret ID' '{nomad_data_dir}/management_token.txt' | awk '{{print $NF}}')",
            f"cd {repo_dir}",
            f"nomad acl policy apply -description 'Task Runner policy' -token '$management_token' task-runner './nomad/nomad_node_configs/task_runner.policy.hcl'",
            f"nomad acl token create -name='Task Runner token' -policy=task-runner -type=client -token '$management_token' 2>&1 | sudo tee {nomad_data_dir}/task_runner_token.txt > /dev/null",
            f"task_runner_token=$(grep 'Secret ID' '{nomad_data_dir}/task_runner_token.txt' | awk '{{print $NF}}')",
            f"nomad var put -namespace default -token '$management_token' -force nomad/jobs task_runner_token=$task_runner_token > /dev/null",
        ]

        self.ssh_client_handler.execute_command(
            commands,
            self.nomad_server_private_ip,
            use_jump=(self.web_ingress_private_ip != self.nomad_server_private_ip),
        )

    def start_nomad_clients(self):
        self.logger.info("Starting Nomad Clients")

        # List of client IPs excluding the server's IP
        nomad_client_private_ips = [
            node["private_ip"]
            for node in self.config["nodes"]
            if node["private_ip"] != self.nomad_server_private_ip
        ]

        for nomad_client_private_ip in nomad_client_private_ips:
            node_pool = next(
                (
                    "default"
                    if node.get("web_ingress", {}).get("run_jobs", True)
                    else "web_ingress"
                )
                for node in self.config["nodes"]
                if node["private_ip"] == nomad_client_private_ip
            )

            # Determine SSH command based on whether it's the web ingress node
            if self.web_ingress_private_ip == nomad_client_private_ip:
                node_class = "web_ingress"
            else:
                node_class = "default"

            commands = [
                "tmux has-session -t nomad-agent 2>/dev/null && tmux kill-session -t nomad-agent",
                f"tmux new-session -d -s nomad-agent 'cd {self.repo_dir}; bash ./nomad/nomad_scripts/start_nomad_agent.sh false true {node_pool} {node_class} {self.nomad_server_private_ip} {nomad_client_private_ip} > head.log 2> head.err'",
            ]

            self.ssh_client_handler.execute_command(
                commands,
                nomad_client_private_ip,
                use_jump=(self.web_ingress_private_ip != nomad_client_private_ip),
            )
