#! /bin/bash

node_private_ips=($(jq -r '.nodes[].private_ip' config.json))

web_ingress_private_ip=$(jq -r '.nodes[] | select(has("web_ingress")) | .private_ip' config.json)
web_ingress_public_ip=$(jq -r '.nodes[] | select(has("web_ingress")) | .web_ingress.public_ip' config.json)

node_ssh_username=$(jq -r '.ssh_username' config.json)
web_ingress_ssh_username=$(jq -r '.nodes[] | select(has("web_ingress")) | .web_ingress.ssh_username' config.json)

shared_dir=$(jq -r '.nodes[] | select(has("shared_file_system")) | .shared_file_system.shared_dir' config.json)

# User
status_filename="node_status"
status_file_loc="$shared_dir/$status_filename"
for node_private_ip in "${node_private_ips[@]}"; do
    if [ $web_ingress_private_ip == $node_private_ip ]; then
        node_ssh_command="ssh -o StrictHostKeyChecking=no $web_ingress_ssh_username@$web_ingress_public_ip"
    else
        node_ssh_command="ssh -o StrictHostKeyChecking=no -J $web_ingress_ssh_username@$web_ingress_public_ip $node_ssh_username@$node_private_ip"
    fi
    $node_ssh_command <<EOF
        echo "$node_private_ip | success" | sudo tee -a $status_file_loc
EOF
done


# copying node_status file into local directory

scp "$web_ingress_ssh_username"@$web_ingress_public_ip:$status_file_loc .

line_count=$(wc -l "$status_filename" | awk '{print $1}')

if [ $line_count -ne ${#node_private_ips[@]} ]; then
    echo "Shared directory is not accessible by every node"
    exit 1
else
    echo "Shared directory is accessible by every node"
fi

# Removing node_status file from shared_dir
ssh -o StrictHostKeyChecking=no "$web_ingress_ssh_username"@$web_ingress_public_ip "sudo rm -f $status_file_loc"
rm -f $status_filename
