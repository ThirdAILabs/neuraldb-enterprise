#!/bin/bash

PUBLIC_NFS_IPS=()

json=$(<config.json)

nodes=("HEADNODE_IP" "NFS_CLIENT_IP")
for node in "${nodes[@]}"; do
    echo "$node"
    ips=($(echo $json | jq -r ".${node}[]"))
    for ip in "${ips[@]}"; do
        PUBLIC_NFS_IPS+=("$ip")
    done
done

PUBLIC_NFS_SERVER_IP="${PUBLIC_NFS_IPS[0]}"
NFS_CLIENT="${PUBLIC_NFS_IPS[1]}"
USERNAME=$admin_name
NFS_SHARED_DIR=$nfs_shared_dir
NODEPASSD=$node_password

env SSHPASS="$NODEPASSD" sshpass -d 123 scp -o StrictHostKeyChecking=no -o ProxyCommand="sshpass -e ssh -W %h:%p $USERNAME@$PUBLIC_NFS_SERVER_IP" $license_path $USERNAME@$NFS_CLIENT:$NFS_SHARED_DIR/license 123<<<$NODEPASSD