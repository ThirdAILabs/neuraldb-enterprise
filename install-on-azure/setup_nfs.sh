#!/bin/bash

PUBLIC_NFS_IPS=()

json=$(<config.json)

nodes=("HEADNODE_IP" "PROXY_CLIENT_IP" "CLIENTNODE_IP")
for node in "${nodes[@]}"; do
    echo "$node"
    ips=($(echo $json | jq -r ".${node}[]"))
    for ip in "${ips[@]}"; do
        PUBLIC_NFS_IPS+=("$ip")
    done
done


PRIVATE_NFS_IPS=()

json=$(<config.json)

nodes=("PRIVATE_HEADNODE_IP" "PRIVATE_PROXY_CLIENT_IP" "PRIVATE_CLIENTNODE_IP")
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
sudo apt update
sudo apt install -y nfs-kernel-server
if [ ! -d "$SHARED_DIR" ]; then
    echo "Creating shared directory: $SHARED_DIR"
    sudo mkdir -p "$SHARED_DIR"
    sudo chmod 777 $SHARED_DIR
    sudo chmod g+s $SHARED_DIR
    sudo mkdir -p "$SHARED_DIR/license"
    sudo mkdir -p "$SHARED_DIR/models"
    sudo mkdir -p "$SHARED_DIR/data"
    sudo mkdir -p "$SHARED_DIR/users"
fi
# Add NFS client IPs to /etc/exports
for CLIENT_IP in ${PRIVATE_NFS_CLIENT_IPS[@]}; do
    echo "$SHARED_DIR \$CLIENT_IP(rw,sync,no_subtree_check)" | sudo tee -a /etc/exports
done
sudo exportfs -ra
sudo systemctl start nfs-kernel-server
sudo systemctl enable nfs-kernel-server
# Adjust firewall settings if needed
# sudo ufw allow from $NFS_CLIENT_IP to any port nfs
EOF

# Mount the shared directory on NFS Client nodes
for CLIENT_IP in "${PUBLIC_NFS_CLIENT_IPS[@]}"; do
    ssh -o StrictHostKeyChecking=no "$USERNAME"@$CLIENT_IP <<EOF
sudo apt -y update
sudo apt-get install -y nfs-common
if [ ! -d "$SHARED_DIR" ]; then
    echo "Creating shared directory: $SHARED_DIR"
    sudo mkdir -p "$SHARED_DIR"
fi
sudo mount -t nfs $PRIVATE_NFS_SERVER_IP:$SHARED_DIR $SHARED_DIR
# Add an entry to /etc/fstab for automatic mounting on boot, if needed
echo "$PRIVATE_NFS_SERVER_IP:$SHARED_DIR $SHARED_DIR nfs rw,hard,intr 0 0" | sudo tee -a /etc/fstab
EOF
done