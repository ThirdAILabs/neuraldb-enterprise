from setup_cluster.ssh_client_handler import SSHClientHandler
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
            web_ingress_private_ip=self.web_ingress_private_ip,
            logger=logger,
        )

        self.nomad_server_private_ip = next(
            node["private_ip"]
            for node in self.config["nodes"]
            if "nomad_server" in node
        )

    def get_install_commands(self):
        """
        Retrieves a list of shell commands for installing necessary software components.
        """
    
        return [
            "sudo apt update",
            "command -v wget >/dev/null || sudo apt install -y wget",
            "command -v docker >/dev/null || (wget -O get-docker.sh https://get.docker.com/ && bash get-docker.sh && docker run hello-world)",
            "command -v tmux >/dev/null || sudo apt install -y tmux",
            'keyring_file="/usr/share/keyrings/hashicorp-archive-keyring.gpg" && [ -f "$keyring_file" ] && sudo rm "$keyring_file"; wget -O- https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o "$keyring_file"; echo "deb [signed-by=$keyring_file] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list',
            "sudo apt-get update",
            "sudo apt-get install -y nomad='1.6.2-1'",
            "[ -d neuraldb-enterprise ] || git clone -b acl https://github.com/ThirdAILabs/neuraldb-enterprise.git",
            "cd neuraldb-enterprise && git pull",
        ]

    def deploy(self):
        """
        Executes installation commands on a set of nodes using SSH.
        For each node, it determines if a proxy should be used for the connection and then executes the install commands remotely using an SSH client handler.
        """
        
        install_commands = self.get_install_commands()

        for ip in self.node_private_ips:
            use_proxy = self.web_ingress_private_ip != ip
            self.ssh_client_handler.execute_commands(
                install_commands,
                (ip if use_proxy else self.web_ingress_public_ip),
                use_proxy,
                run_sequentially=True,
            )

    def setup_nomad_cluster(self):
        """
        Set up a Nomad cluster by configuring and launching Nomad server sessions.

        This function configures a Nomad cluster based on the IP settings and
        starts the Nomad server within a new or existing tmux session using predefined
        scripts
        """
    
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

        use_jump = self.web_ingress_private_ip != self.nomad_server_private_ip
        self.ssh_client_handler.execute_commands(
            commands,
            self.nomad_server_private_ip if use_jump else self.web_ingress_public_ip,
            use_jump=use_jump,
            run_sequentially=True,
        )

        # TODO(pratik): do we even need it? given we wait for ssh command to finish.
        time.sleep(20)

    def bootstrap_acl_system(self):
        """
        Initializes and configures the ACL (Access Control List) system for the Nomad server.
        
        - Creates necessary directories for Nomad data.
        - Bootstraps the Nomad ACL system if not already done.
        - Extracts and logs the management token.
        - Applies an ACL policy from a specified file.
        - Creates an ACL token for a specific task runner.
        - Sets up environment variables with the new token.

        """
    
        self.logger.info("Bootstrapping ACL system")

        nomad_data_dir = "/opt/neuraldb_enterprise/nomad_data"
        repo_dir = self.repo_dir

        command = f"""
sudo mkdir -p {nomad_data_dir}
if [ ! -f "{nomad_data_dir}/management_token.txt" ]; then sudo bash -c 'nomad acl bootstrap > {nomad_data_dir}/management_token.txt 2>&1'; fi
management_token=$(grep "Secret ID" "{nomad_data_dir}/management_token.txt" | awk '{{print $NF}}')
echo "Management Token successfully extracted: $management_token"
cd {repo_dir}
nomad acl policy apply -description "Task Runner policy" -token "$management_token" task-runner "./nomad/nomad_node_configs/task_runner.policy.hcl"
nomad acl token create -name="Task Runner token" -policy=task-runner -type=client -token "$management_token" 2>&1 | sudo tee {nomad_data_dir}/task_runner_token.txt > /dev/null
task_runner_token=$(grep "Secret ID" "{nomad_data_dir}/task_runner_token.txt" | awk '{{print $NF}}')
echo "TaskRunner Token successfully extracted: $task_runner_token"
nomad var put -namespace default -token "$management_token" -force nomad/jobs task_runner_token=$task_runner_token > /dev/null
"""

        use_jump = self.web_ingress_private_ip != self.nomad_server_private_ip
        self.ssh_client_handler.execute_commands(
            [command],
            self.nomad_server_private_ip if use_jump else self.web_ingress_public_ip,
            use_jump=(self.web_ingress_private_ip != self.nomad_server_private_ip),
            run_sequentially=True,
        )

    def start_nomad_clients(self):
        """
        Starts Nomad client agents on specified nodes except the node acting as the Nomad server.

        This method iterates through a list of client IPs derived from the node configuration,
        excluding the IP of the Nomad server. It then determines the appropriate pool and class
        for each node based on its configuration and executes commands over SSH to start the
        Nomad client agents in a new detached tmux session.

        """
    
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
            use_jump = self.web_ingress_private_ip != nomad_client_private_ip
            self.ssh_client_handler.execute_commands(
                commands,
                nomad_client_private_ip if use_jump else self.web_ingress_public_ip,
                use_jump=use_jump,
                run_sequentially=True,
            )
