#! /bin/bash

PUBLIC_NFS_SERVER_IP=$(jq -r '.HEADNODE_IP | .[0]' config.json)
USERNAME=$admin_name

mount_point="/opt/neuraldb_enterprise"
shared_dir="$mount_point/model_bazaar"
echo "Mounting shared drive at $mount_point"

# Finding the Logical unit number of the attached data disk
disk_lun=$(az vm show --resource-group $resource_group_name --name Head --query "storageProfile.dataDisks[?name=='DataDisk'].lun" -o tsv)
ssh -o StrictHostKeyChecking=no "$USERNAME"@$PUBLIC_NFS_SERVER_IP <<EOF
    sudo apt -y update
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

# Updating or Adding setup_nfs and shared_dir variables in the variable.sh file of install
file_path="../install/variables.sh"
sed -i '' "s/^setup_nfs=.*/setup_nfs=true/" $file_path
sed -i '' "s|^shared_dir=.*|shared_dir=$shared_dir|" $file_path