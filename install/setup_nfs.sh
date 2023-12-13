#!/bin/bash

PUBLIC_NFS_IPS=()

json=$(<config.json)

nodes=("HEADNODE_IP" "CLIENTNODE_IP")
for node in "${nodes[@]}"; do
    echo "$node"
    ips=($(echo $json | jq -r ".${node}[]"))
    for ip in "${ips[@]}"; do
        PUBLIC_NFS_IPS+=("$ip")
    done
done


PRIVATE_NFS_IPS=()

json=$(<config.json)

nodes=("PRIVATE_HEADNODE_IP" "PRIVATE_CLIENTNODE_IP")
for node in "${nodes[@]}"; do
    echo "$node"
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

SHARED_DIR=$nfs_shared_dir
USERNAME=$admin_name

# Install NFS Server on the NFS Server node
ssh -o StrictHostKeyChecking=no "$USERNAME"@$PUBLIC_NFS_SERVER_IP <<EOF
echo "$sudo_password" | sudo -S apt update
echo "$sudo_password" | sudo -S apt install -y nfs-kernel-server
if [ ! -d "$SHARED_DIR" ]; then
    echo "Creating shared directory: $SHARED_DIR"
    echo "$sudo_password" | sudo -S mkdir -p "$SHARED_DIR"
    echo "$sudo_password" | sudo -S chmod 777 $SHARED_DIR
    echo "$sudo_password" | sudo -S groupadd -g 4646 nomad_nfs || true
    echo "$sudo_password" | sudo -S useradd -u 4646 -g 4646 nomad_nfs || true
    echo "$sudo_password" | sudo -S chown :4646 $SHARED_DIR
    echo "$sudo_password" | sudo -S chmod g+s $SHARED_DIR
    mkdir -p "$SHARED_DIR/license"
    mkdir -p "$SHARED_DIR/models"
    mkdir -p "$SHARED_DIR/data"
    mkdir -p "$SHARED_DIR/users"
fi
# Add NFS client IPs to /etc/exports
for CLIENT_IP in ${PRIVATE_NFS_CLIENT_IPS[@]}; do
    export_line="$SHARED_DIR \$CLIENT_IP(rw,sync,no_subtree_check,all_squash,anonuid=4646,anongid=4646)"
    if ! grep -qF -- "\$export_line" /etc/exports; then
        echo "Adding NFS export for \$CLIENT_IP"
        echo "\$export_line" | echo "$sudo_password" | sudo -S tee -a /etc/exports
    else
        echo "NFS export for \$CLIENT_IP already exists"
    fi
done
echo "$sudo_password" | sudo -S exportfs -ra
echo "$sudo_password" | sudo -S systemctl start nfs-kernel-server
echo "$sudo_password" | sudo -S systemctl enable nfs-kernel-server
# Adjust firewall settings if needed
# echo "$sudo_password" | sudo -S ufw allow from $NFS_CLIENT_IP to any port nfs
EOF


# Mount the shared directory on NFS Client nodes
for CLIENT_IP in "${PUBLIC_NFS_CLIENT_IPS[@]}"; do
    ssh -o StrictHostKeyChecking=no "$USERNAME"@$CLIENT_IP <<EOF
echo "$sudo_password" | sudo -S apt -y update
echo "$sudo_password" | sudo -S apt-get install -y nfs-common
if [ ! -d "$SHARED_DIR" ]; then
    echo "Creating shared directory: $SHARED_DIR"
    echo "$sudo_password" | sudo -S mkdir -p "$SHARED_DIR"
fi
echo "$sudo_password" | sudo -S mount -t nfs $PRIVATE_NFS_SERVER_IP:$SHARED_DIR $SHARED_DIR
# Add an entry to /etc/fstab for automatic mounting on boot, if needed
export_line="$PRIVATE_NFS_SERVER_IP:$SHARED_DIR $SHARED_DIR nfs rw,hard,intr 0 0"
if ! grep -qF -- "\$export_line" /etc/fstab; then
    echo "Adding NFS mount for $CLIENT_IP"
    echo "\$export_line" | echo "$sudo_password" | sudo -S tee -a /etc/fstab
else
    echo "NFS mount for $CLIENT_IP already exists"
fi
EOF
done