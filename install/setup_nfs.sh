#!/bin/bash

PUBLIC_NFS_IPS=()

json=$(<config.json)

nodes=("HEADNODE_IP")
for node in "${nodes[@]}"; do
    echo "$node"
    ips=($(echo $json | jq -r ".${node}[]"))
    for ip in "${ips[@]}"; do
        PUBLIC_NFS_IPS+=("$ip")
    done
done

NFS_CLIENTS=()

json=$(<config.json)

nodes=("NFS_CLIENT_IP")
for node in "${nodes[@]}"; do
    echo "$node"
    ips=($(echo $json | jq -r ".${node}[]"))
    for ip in "${ips[@]}"; do
        NFS_CLIENTS+=("$ip")
    done
done


PRIVATE_NFS_CLIENT_IPS=()

json=$(<config.json)

nodes=("PRIVATE_CLIENTNODE_IP")
for node in "${nodes[@]}"; do
    echo "$node"
    ips=($(echo $json | jq -r ".${node}[]"))
    for ip in "${ips[@]}"; do
        PRIVATE_NFS_CLIENT_IPS+=("$ip")
    done
done

# NFS Server Configuration
PUBLIC_NFS_SERVER_IP="${PUBLIC_NFS_IPS[0]}"


# Array of NFS Client IPs
NFS_CLIENT="${NFS_CLIENTS[0]}"

SHARED_DIR=$nfs_shared_dir
USERNAME=$admin_name
NODEPASSD=$node_password

# Install NFS Server on the NFS Server node
env SSHPASS="$NODEPASSD" sshpass -d 123 ssh -o ProxyCommand="sshpass -e ssh -W %h:%p $USERNAME@$PUBLIC_NFS_SERVER_IP" $USERNAME@$NFS_CLIENT 123<<<$NODEPASSD <<EOF
sudo apt update
sudo apt install -y nfs-kernel-server
if [ ! -d "$SHARED_DIR" ]; then
    echo "Creating shared directory: $SHARED_DIR"
    sudo mkdir -p "$SHARED_DIR"
    sudo chmod 777 $SHARED_DIR
    sudo groupadd -g 4646 nomad_nfs || true
    sudo useradd -u 4646 -g 4646 nomad_nfs || true
    sudo chown :4646 $SHARED_DIR
    sudo chmod g+s $SHARED_DIR
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
        echo "\$export_line" | sudo tee -a /etc/exports
    else
        echo "NFS export for \$CLIENT_IP already exists"
    fi
done
sudo exportfs -ra
sudo systemctl start nfs-kernel-server
sudo systemctl enable nfs-kernel-server
# Adjust firewall settings if needed
# sudo ufw allow from $NFS_CLIENT_IP to any port nfs
EOF


# Mount the shared directory on NFS Client nodes
for CLIENT_IP in "${PRIVATE_NFS_CLIENT_IPS[@]}"; do
    env SSHPASS="$NODEPASSD" sshpass -d 123 ssh -o ProxyCommand="sshpass -e ssh -W %h:%p $USERNAME@$PUBLIC_NFS_SERVER_IP" $USERNAME@$CLIENT_IP 123<<<$NODEPASSD <<EOF
sudo apt -y update
sudo apt-get install -y nfs-common
if [ ! -d "$SHARED_DIR" ]; then
    echo "Creating shared directory: $SHARED_DIR"
    sudo mkdir -p "$SHARED_DIR"
fi
sudo mount -t nfs $NFS_CLIENT:$SHARED_DIR $SHARED_DIR
# Add an entry to /etc/fstab for automatic mounting on boot, if needed
export_line="$NFS_CLIENT:$SHARED_DIR $SHARED_DIR nfs rw,hard,intr 0 0"
if ! grep -qF -- "\$export_line" /etc/fstab; then
    echo "Adding NFS mount for $CLIENT_IP"
    echo "\$export_line" | sudo tee -a /etc/fstab
else
    echo "NFS mount for $CLIENT_IP already exists"
fi
EOF
done