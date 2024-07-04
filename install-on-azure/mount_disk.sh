#! /bin/bash

source variables.sh

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

mount_point="/opt/neuraldb_enterprise"
echo "Mounting shared drive at $mount_point"

# Finding the Logical unit number of the attached data disk
disk_lun=$(az vm show --resource-group $resource_group_name --name Head --query "storageProfile.dataDisks[?name=='DataDisk'].lun" -o tsv)
$shared_file_system_ssh_command <<EOF
    sudo yum -y check-update
    device_name="/dev/\$(ls -l /dev/disk/azure/scsi1 | grep -oE "lun$disk_lun -> ../../../[a-z]+" | awk -F'/' '{print \$NF}')"
    sudo mkfs.xfs \$device_name
    sudo mkdir -p $mount_point
    sudo mount \$device_name $mount_point
    fstab_entry="\$device_name   $mount_point   xfs   defaults   0   0"
    if ! grep -qF -- "\$fstab_entry" /etc/fstab; then
        echo "\$fstab_entry" | sudo tee -a /etc/fstab
    else
        echo "fstab entry already exists"
    fi
EOF
