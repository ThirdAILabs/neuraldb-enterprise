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

PUBLIC_NFS_CLIENT_IP="${PUBLIC_NFS_IPS[1]}"

scp $license_path "$USERNAME"@$PUBLIC_NFS_CLIENT_IP:/model_bazaar/license/