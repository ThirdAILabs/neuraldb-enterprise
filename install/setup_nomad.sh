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
        sudo yum -y check-update

        # Install wget
        if ! command -v wget &> /dev/null; then
            echo "wget not found. Installing..."
            sudo yum install -y wget
        else
            echo "wget is already installed."
        fi

        # Install git
        if ! command -v git &> /dev/null; then
            echo "git not found. Installing..."
            sudo yum install -y git
        else
            echo "git is already installed."
        fi

        # Install docker
        if ! command -v docker &> /dev/null; then
            sudo yum update -y
            sudo yum install docker -y
            sudo systemctl start docker
            sudo docker run hello-world
            sudo systemctl enable docker
            sudo usermod -a -G docker \$(whoami)
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
        sudo yum -y check-update
        sudo yum install -y yum-utils
        sudo yum-config-manager --add-repo https://rpm.releases.hashicorp.com/AmazonLinux/hashicorp.repo
        sudo yum -y install nomad

        # Cloning neuraldb-enterprise repo
        rm -rf "$repo_dir" && git clone "$repo_url" && cd "$repo_dir"

EOF
done


echo "Setting up Nomad Cluster..."

nomad_server_private_ip=$(jq -r '.nodes[] | select(has("nomad_server")) | .private_ip' config.json)

if [ $web_ingress_private_ip == $nomad_server_private_ip ]; then
    nomad_server_ssh_command="ssh -o StrictHostKeyChecking=no $web_ingress_ssh_username@$web_ingress_public_ip"
    node_class="web_ingress"
else
    nomad_server_ssh_command="ssh -o StrictHostKeyChecking=no -J $web_ingress_ssh_username@$web_ingress_public_ip $node_ssh_username@$nomad_server_private_ip"
    node_class="default"
fi


echo "Starting Initial Nomad Server"

node_pool=$(jq -r --arg ip "$nomad_server_private_ip" '.nodes[] | select(.private_ip == $ip) | .web_ingress.run_jobs as $run_jobs | if $run_jobs == null or $run_jobs == true then "default" else "web_ingress" end' config.json)
$nomad_server_ssh_command <<EOF
    tmux has-session -t nomad-agent 2>/dev/null && tmux kill-session -t nomad-agent
    tmux new-session -d -s nomad-agent 'cd neuraldb-enterprise; bash ./nomad/nomad_scripts/start_nomad_agent.sh true true $node_pool $node_class $nomad_server_private_ip $nomad_server_private_ip > head.log 2> head.err'
EOF
sleep 20  # Wait until server is running to continue setup


echo "Bootstrapping ACL system"

nomad_data_dir=/opt/neuraldb_enterprise/nomad_data

$nomad_server_ssh_command <<EOF
    sudo mkdir -p $nomad_data_dir
    if [ ! -f "$nomad_data_dir/management_token.txt" ]; then
        sudo bash -c "nomad acl bootstrap > $nomad_data_dir/management_token.txt 2>&1"
    fi
    management_token=\$(grep 'Secret ID' "$nomad_data_dir/management_token.txt"  | awk '{print \$NF}')
    cd "$repo_dir"
    nomad acl policy apply -description "Task Runner policy" -token "\$management_token" task-runner "./nomad/nomad_node_configs/task_runner.policy.hcl"
    nomad acl token create -name="Task Runner token" -policy=task-runner -type=client -token "\$management_token" 2>&1 | sudo tee $nomad_data_dir/task_runner_token.txt > /dev/null
    task_runner_token=\$(grep 'Secret ID' "$nomad_data_dir/task_runner_token.txt"  | awk '{print \$NF}')
    nomad var put -namespace default -token "\$management_token" -force nomad/jobs task_runner_token=\$task_runner_token > /dev/null
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
