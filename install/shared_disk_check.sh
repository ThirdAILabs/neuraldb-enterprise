#! /bin/bash

PUBLIC_NFS_IPS=()

json=$(<config.json)

nodes=("HEADNODE_IP" "CLIENTNODE_IP")
for node in "${nodes[@]}"; do
    ips=($(echo $json | jq -r ".${node}[]"))
    for ip in "${ips[@]}"; do
        PUBLIC_NFS_IPS+=("$ip")
    done
done

# NFS Server Configuration
PUBLIC_NFS_SERVER_IP="${PUBLIC_NFS_IPS[0]}"

# Array of NFS Client IPs
PUBLIC_NFS_CLIENT_IPS=("${PUBLIC_NFS_IPS[@]:1}")


# User
USERNAME=$admin_name
status_filename="node_status"
status_file_loc="$shared_dir/$status_filename"

# Headnode connectivity check
ssh -o StrictHostKeyChecking=no "$USERNAME"@$PUBLIC_NFS_SERVER_IP <<EOF
    echo "$PUBLIC_NFS_SERVER_IP | success" | sudo tee $status_file_loc
EOF

# Client node connectivity check
for CLIENT_IP in "${PUBLIC_NFS_CLIENT_IPS[@]}"; do
    ssh -o StrictHostKeyChecking=no "$USERNAME"@$CLIENT_IP <<EOF
echo "$CLIENT_IP | success" | sudo tee -a $status_file_loc
EOF
done

# copying node_status file into local directory

scp "$USERNAME"@$PUBLIC_NFS_SERVER_IP:$status_file_loc .

line_count=$(wc -l "$status_filename" | awk '{print $1}')

if [ $line_count -ne ${#PUBLIC_NFS_IPS[@]} ]; then
    echo "Shared directory is not accessible by every node"
    exit 1
else
    echo "Shared directory is accessible by every node"
fi

# Removing node_status file from shared_dir
ssh -o StrictHostKeyChecking=no "$USERNAME"@$PUBLIC_NFS_SERVER_IP "sudo rm -f $status_file_loc"
rm -f $status_filename
