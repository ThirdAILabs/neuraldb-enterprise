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

PUBLIC_NFS_SERVER_IP="${PUBLIC_NFS_IPS[0]}"
USERNAME=$admin_name

scp $license_path "$USERNAME"@$PUBLIC_NFS_SERVER_IP:/model_bazaar/license/