#!/bin/bash

source variables.sh


echo "Installing Nomad and dependencies"

node_private_ips=($(jq -r '.nodes[].private_ip' config.json))

web_ingress_private_ip=$(jq -r '.nodes[] | select(has("web_ingress")) | .private_ip' config.json)
web_ingress_public_ip=$(jq -r '.nodes[] | select(has("web_ingress")) | .web_ingress.public_ip' config.json)

node_ssh_username=$(jq -r '.ssh_username' config.json)
web_ingress_ssh_username=$(jq -r '.nodes[] | select(has("web_ingress")) | .web_ingress.ssh_username' config.json)

repo_url="https://github.com/ThirdAILabs/neuraldb-enterprise.git"
repo_dir="neuraldb-enterprise"

for node_private_ip in "${node_private_ips[@]}"; do
    if [ $web_ingress_private_ip == $node_private_ip ]; then
        node_ssh_command="ssh -o StrictHostKeyChecking=no $web_ingress_ssh_username@$web_ingress_public_ip"
    else
        node_ssh_command="ssh -o StrictHostKeyChecking=no -J $web_ingress_ssh_username@$web_ingress_public_ip $node_ssh_username@$node_private_ip"
    fi
    $node_ssh_command <<EOF
        sudo apt update

        # Install wget
        if ! command -v wget &> /dev/null; then
            echo "wget not found. Installing..."
            sudo apt install -y wget
        else
            echo "wget is already installed."
        fi

        # Install docker
        if ! command -v docker &> /dev/null; then
            wget -O get-docker.sh https://get.docker.com/
            bash get-docker.sh
            docker run hello-world
        else
            echo "Docker is already installed."
        fi

        # Install tmux
        if ! command -v tmux &> /dev/null; then
            echo "tmux not found. Installing..."
            sudo apt install -y tmux
        else
            echo "tmux is already installed."
        fi

        # Install nomad
        keyring_file="/usr/share/keyrings/hashicorp-archive-keyring.gpg"
        if [ -f "\$keyring_file" ]; then
            # Remove the existing keyring file to avoid the prompt
            sudo rm "\$keyring_file"
        fi
        wget -O- https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o "\$keyring_file"
        echo "deb [signed-by=\$keyring_file] https://apt.releases.hashicorp.com \$(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
        sudo apt-get update && sudo apt-get install -y nomad="1.6.2-1"

        # Cloning neuraldb-enterprise repo
        if [ -d "$repo_dir" ]; then
            # If the directory exists, cd into it and pull the latest updates
            echo "Directory $repo_dir already exists. Pulling latest updates..."
            cd "$repo_dir" && git pull
        else
            # If the directory does not exist, clone the repository
            echo "Cloning repository..."
            git clone "$repo_url" && cd "$repo_dir"
        fi
EOF
done


echo "Starting Initial Nomad Server"

nomad_server_private_ip=$(jq -r '.nodes[] | select(has("nomad_server")) | .private_ip' config.json)
node_pool=$(jq -r --arg ip "$nomad_server_private_ip" '.nodes[] | select(.private_ip == $ip) | .web_ingress.run_jobs as $run_jobs | if $run_jobs == null or $run_jobs == true then "default" else "web_ingress" end' config.json)

if [ $web_ingress_private_ip == $nomad_server_private_ip ]; then
    nomad_server_ssh_command="ssh -o StrictHostKeyChecking=no $web_ingress_ssh_username@$web_ingress_public_ip"
    node_class="web_ingress"
else
    nomad_server_ssh_command="ssh -o StrictHostKeyChecking=no -J $web_ingress_ssh_username@$web_ingress_public_ip $node_ssh_username@$nomad_server_private_ip"
    node_class="default"
fi

$nomad_server_ssh_command <<EOF
    tmux has-session -t nomad-agent 2>/dev/null && tmux kill-session -t nomad-agent
    tmux new-session -d -s nomad-agent 'cd neuraldb-enterprise; bash ./nomad/nomad_scripts/start_nomad_agent.sh true true $node_pool $node_class $nomad_server_private_ip $nomad_server_private_ip > head.log 2> head.err'
EOF


echo "Starting Nomad Clients"

nomad_client_private_ips=($(jq -r --arg ip "$nomad_server_private_ip" '.nodes[] | select(.private_ip != $ip) | .private_ip' config.json))

for nomad_client_private_ip in "${nomad_client_private_ips[@]}"; do

    node_pool=$(jq -r --arg ip "$nomad_client_private_ip" '.nodes[] | select(.private_ip == $ip) | .web_ingress.run_jobs as $run_jobs | if $run_jobs == null or $run_jobs == true then "default" else "web_ingress" end' config.json)

    if [ $web_ingress_private_ip == $nomad_client_private_ip ]; then
        nomad_client_ssh_command="ssh -o StrictHostKeyChecking=no $web_ingress_ssh_username@$web_ingress_public_ip"
        node_class="web_ingress"
    else
        nomad_client_ssh_command="ssh -o StrictHostKeyChecking=no -J $web_ingress_ssh_username@$web_ingress_public_ip $node_ssh_username@$nomad_client_private_ip"
        node_class="default"
    fi

    $nomad_client_ssh_command <<EOF
        tmux has-session -t nomad-agent 2>/dev/null && tmux kill-session -t nomad-agent
        tmux new-session -d -s nomad-agent 'cd neuraldb-enterprise; bash ./nomad/nomad_scripts/start_nomad_agent.sh false true $node_pool $node_class $nomad_server_private_ip $nomad_client_private_ip > head.log 2> head.err'
EOF
done
