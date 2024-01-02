#!/bin/bash

PUBLIC_NFS_IPS=()

json=$(<config.json)

nodes=("HEADNODE_IP" "CLIENTNODE_IP")
for node in "${nodes[@]}"; do
    ips=($(echo $json | jq -r ".${node}[]"))
    for ip in "${ips[@]}"; do
        PUBLIC_NFS_IPS+=("$ip")
    done
done


PRIVATE_NFS_IPS=()

json=$(<config.json)

nodes=("PRIVATE_HEADNODE_IP" "PRIVATE_CLIENTNODE_IP")
for node in "${nodes[@]}"; do
    ips=($(echo $json | jq -r ".${node}[]"))
    for ip in "${ips[@]}"; do
        PRIVATE_NFS_IPS+=("$ip")
    done
done

# NFS Server Configuration
PUBLIC_NFS_SERVER_IP="${PUBLIC_NFS_IPS[0]}"
PRIVATE_NFS_SERVER_IP="${PRIVATE_NFS_IPS[0]}"


# Array of NFS Client IPs
PUBLIC_NFS_CLIENT_IPS=("${PUBLIC_NFS_IPS[@]:1}")
PRIVATE_NFS_CLIENT_IPS=("${PRIVATE_NFS_IPS[@]:1}")

USERNAME=$admin_name

ssh -o StrictHostKeyChecking=no "$USERNAME"@$PUBLIC_NFS_SERVER_IP <<EOF
    sudo apt -y update
    sudo groupadd -g 4646 nomad_nfs || true
    sudo useradd -u 4646 -g 4646 nomad_nfs || true
    sudo usermod -a -G 4646 $USERNAME
    sudo mkdir -p $shared_dir
    sudo mkdir "$shared_dir/license"
    sudo mkdir "$shared_dir/models"
    sudo mkdir "$shared_dir/data"
    sudo mkdir "$shared_dir/users"
    sudo chown -R :4646 $shared_dir
    sudo chmod -R 774 $shared_dir
    sudo chmod -R g+s $shared_dir
EOF

# Install NFS Server on the NFS Server node
if [ "$setup_nfs" == true ]; then
    ssh -o StrictHostKeyChecking=no "$USERNAME"@$PUBLIC_NFS_SERVER_IP <<EOF
    sudo apt install -y nfs-kernel-server
    sudo apt install -y acl
    sudo setfacl -d -R -m u::rwx,g::rwx,o::r $shared_dir

    # Add NFS client IPs to /etc/exports
    for CLIENT_IP in ${PRIVATE_NFS_CLIENT_IPS[@]}; do
        export_line="$shared_dir \$CLIENT_IP(rw,sync,no_subtree_check,all_squash,anonuid=4646,anongid=4646)"
        if ! grep -qF -- "\$export_line" /etc/exports; then
            echo "Adding NFS export for \$CLIENT_IP"
            echo "\$export_line" | sudo tee -a /etc/exports
        else
            echo "NFS export for \$CLIENT_IP already exists"
        fi
    done
    sudo exportfs -ra
    if sudo systemctl is-active --quiet nfs-kernel-server; then
        sudo systemctl restart nfs-kernel-server
    else
        sudo systemctl start nfs-kernel-server
    fi
    sudo systemctl enable nfs-kernel-server
    # Adjust firewall settings if needed
    # sudo ufw allow from $NFS_CLIENT_IP to any port nfs
EOF

    # Mount the shared directory on NFS Client nodes
    for CLIENT_IP in "${PUBLIC_NFS_CLIENT_IPS[@]}"; do
        ssh -o StrictHostKeyChecking=no "$USERNAME"@$CLIENT_IP <<EOF
        sudo apt -y update
        sudo apt-get install -y nfs-common
        if [ ! -d "$shared_dir" ]; then
            echo "Creating shared directory: $shared_dir"
            sudo mkdir -p "$shared_dir"
        fi
        sudo mount -t nfs $PRIVATE_NFS_SERVER_IP:$shared_dir $shared_dir
        # Add an entry to /etc/fstab for automatic mounting on boot, if needed
        export_line="$PRIVATE_NFS_SERVER_IP:$shared_dir $shared_dir nfs rw,hard,intr 0 0"
        if ! grep -qF -- "\$export_line" /etc/fstab; then
            echo "Adding NFS mount for $CLIENT_IP"
            echo "\$export_line" | sudo tee -a /etc/fstab
        else
            echo "NFS mount for $CLIENT_IP already exists"
        fi
EOF
    done
fi