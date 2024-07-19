#!/bin/bash

source variables.sh

echo "Installing Nomad and dependencies"

sudo yum -y check-update

# Install wget
if ! command -v wget &> /dev/null; then
    echo "wget not found. Installing..."
    sudo yum install -y wget
else
    echo "wget is already installed."
fi

# Install docker
if ! command -v docker &> /dev/null; then
    sudo yum update -y
    sudo yum install docker -y
    sudo systemctl start docker
    sudo docker run hello-world
    sudo systemctl enable docker
    sudo usermod -a -G docker $(whoami)
    newgrp docker
else
    echo "Docker is already installed."
fi

# Install tmux
if ! command -v tmux &> /dev/null; then
    echo "tmux not found. Installing..."
    sudo yum install -y tmux
else
    echo "tmux is already installed."
fi

# Install nomad
# Update repository list and install Nomad
sudo yum -y check-update
sudo yum install -y yum-utils
sudo yum-config-manager --add-repo https://rpm.releases.hashicorp.com/AmazonLinux/hashicorp.repo
sudo yum -y install nomad


echo "Setting up Nomad Cluster..."

nomad_server_private_ip=$(jq -r '.nodes[] | select(has("nomad_server")) | .private_ip' config.json)
node_class="web_ingress"


echo "Starting Initial Nomad Server"

node_pool=$(jq -r --arg ip "$nomad_server_private_ip" '.nodes[] | select(.private_ip == $ip) | .web_ingress.run_jobs as $run_jobs | if $run_jobs == null or $run_jobs == true then "default" else "web_ingress" end' config.json)
tmux has-session -t nomad-agent 2>/dev/null && tmux kill-session -t nomad-agent
tmux new-session -d -s nomad-agent 'cd neuraldb-enterprise; bash ./nomad/nomad_scripts/start_nomad_agent.sh true true $node_pool $node_class $nomad_server_private_ip $nomad_server_private_ip > head.log 2> head.err'
sleep 10  # Wait until server is running to continue setup


echo "Bootstrapping ACL system"

nomad_data_dir=/opt/neuraldb_enterprise/nomad_data

sudo mkdir -p $nomad_data_dir
if [ ! -f "$nomad_data_dir/management_token.txt" ]; then
    sudo bash -c "nomad acl bootstrap > $nomad_data_dir/management_token.txt 2>&1"
fi
management_token=$(grep 'Secret ID' "$nomad_data_dir/management_token.txt"  | awk '{print $NF}')

nomad acl policy apply -description "Task Runner policy" -token "$management_token" task-runner "../nomad/nomad_node_configs/task_runner.policy.hcl"
nomad acl token create -name="Task Runner token" -policy=task-runner -type=client -token "$management_token" 2>&1 | sudo tee $nomad_data_dir/task_runner_token.txt > /dev/null
task_runner_token=$(grep 'Secret ID' "$nomad_data_dir/task_runner_token.txt"  | awk '{print $NF}')
nomad var put -namespace default -token "$management_token" -force nomad/jobs task_runner_token=$task_runner_token > /dev/null
