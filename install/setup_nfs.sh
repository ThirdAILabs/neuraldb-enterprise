#!/bin/bash

shared_file_system_private_ip=$(jq -r '.nodes[] | select(has("shared_file_system")) | .private_ip' config.json)

web_ingress_private_ip=$(jq -r '.nodes[] | select(has("web_ingress")) | .private_ip' config.json)
web_ingress_public_ip=$(jq -r '.nodes[] | select(has("web_ingress")) | .web_ingress.public_ip' config.json)

node_ssh_username=$(jq -r '.ssh_username' config.json)
web_ingress_ssh_username=$(jq -r '.nodes[] | select(has("web_ingress")) | .web_ingress.ssh_username' config.json)

if [ $web_ingress_private_ip == $shared_file_system_private_ip ]; then
    shared_file_system_ssh_command="ssh -o StrictHostKeyChecking=no $web_ingress_ssh_username@$web_ingress_public_ip"
else
    shared_file_system_ssh_command="ssh -o StrictHostKeyChecking=no -J $web_ingress_ssh_username@$web_ingress_public_ip $node_ssh_username@$shared_file_system_private_ip"
fi


shared_dir=$(jq -r '.nodes[] | select(has("shared_file_system")) | .shared_file_system.shared_dir' config.json)

$shared_file_system_ssh_command <<EOF
    sudo apt -y update
    sudo groupadd -g 4646 nomad_nfs || true
    sudo useradd -u 4646 -g 4646 nomad_nfs || true
    sudo usermod -a -G 4646 $node_ssh_username
    sudo mkdir -p $shared_dir
    sudo mkdir -p "$shared_dir/license"
    sudo mkdir -p "$shared_dir/models"
    sudo mkdir -p "$shared_dir/data"
    sudo mkdir -p "$shared_dir/users"
    sudo chown -R :4646 $shared_dir
    sudo chmod -R 774 $shared_dir
    sudo chmod -R g+s $shared_dir
EOF


create_nfs_server=$(jq -r '.nodes[] | select(has("shared_file_system")) | .shared_file_system.create_nfs_server' config.json)

# Install NFS Server on the NFS Server node
if [ $create_nfs_server == "true"  ]; then
    nfs_client_private_ips=($(jq -r --arg ip "$shared_file_system_private_ip" '.nodes[] | select(.private_ip != $ip) | .private_ip' config.json))
    $shared_file_system_ssh_command <<EOF
        sudo apt install -y nfs-kernel-server
        sudo apt install -y acl
        sudo setfacl -d -R -m u::rwx,g::rwx,o::r $shared_dir

        # Add NFS client IPs to /etc/exports
        for nfs_client_private_ip in ${nfs_client_private_ips[@]}; do
            export_line="$shared_dir \$nfs_client_private_ip(rw,sync,no_subtree_check,all_squash,anonuid=4646,anongid=4646)"
            if ! grep -qF -- "\$export_line" /etc/exports; then
                echo "Adding NFS export for \$nfs_client_private_ip"
                echo "\$export_line" | sudo tee -a /etc/exports
            else
                echo "NFS export for \$nfs_client_private_ip already exists"
            fi
        done
        sudo exportfs -ra
        if sudo systemctl is-active --quiet nfs-kernel-server; then
            sudo systemctl restart nfs-kernel-server
        else
            sudo systemctl start nfs-kernel-server
        fi
        sudo systemctl enable nfs-kernel-server
EOF


    # Mount the shared directory on NFS Client nodes
    for nfs_client_private_ip in "${nfs_client_private_ips[@]}"; do
        if [ $web_ingress_private_ip == $nfs_client_private_ip ]; then
            shared_file_system_ssh_command="ssh -o StrictHostKeyChecking=no $web_ingress_ssh_username@$web_ingress_public_ip"
        else
            shared_file_system_ssh_command="ssh -o StrictHostKeyChecking=no -J $web_ingress_ssh_username@$web_ingress_public_ip $node_ssh_username@$nfs_client_private_ip"
        fi
        $shared_file_system_ssh_command <<EOF
            sudo apt -y update
            sudo apt-get install -y nfs-common
            if [ ! -d "$shared_dir" ]; then
                echo "Creating shared directory: $shared_dir"
                sudo mkdir -p "$shared_dir"
            fi
            sudo mount -t nfs $shared_file_system_private_ip:$shared_dir $shared_dir
            # Add an entry to /etc/fstab for automatic mounting on boot, if needed
            export_line="$shared_file_system_private_ip:$shared_dir $shared_dir nfs rw,hard,intr 0 0"
            if ! grep -qF -- "\$export_line" /etc/fstab; then
                echo "Adding NFS mount for $nfs_client_private_ip"
                echo "\$export_line" | sudo tee -a /etc/fstab
            else
                echo "NFS mount for $nfs_client_private_ip already exists"
            fi
EOF
    done
fi