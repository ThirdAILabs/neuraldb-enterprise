#!/bin/bash

source variables.sh

web_ingress_public_ip=$(jq -r '.nodes[] | select(has("web_ingress")) | .web_ingress.public_ip' config.json)
web_ingress_ssh_username=$(jq -r '.nodes[] | select(has("web_ingress")) | .web_ingress.ssh_username' config.json)

ssh_command="ssh -o StrictHostKeyChecking=no $web_ingress_ssh_username@$web_ingress_public_ip"

$ssh_command <<EOF
    # Create the mount point path
    if [ ! -d "$volume_mount_point" ]; then
        sudo mkdir -p $volume_mount_point
    fi

    # Check if the volume is new or already formatted. If new, format it.
    if sudo blkid $volume_device_name &>/dev/null; then
        echo "The volume $volume_device_name is already formatted."
    else
        echo "The volume $volume_device_name is not formatted. Formatting it as ext4."
        sudo mkfs -t ext4 $volume_device_name
    fi

    # Mount the volume
    echo "Mounting the volume $volume_device_name to $volume_mount_point."
    sudo mount $volume_device_name $volume_mount_point

    # Update /etc/fstab to mount the volume automatically after reboot
    FSTAB_ENTRY="$volume_device_name $volume_mount_point ext4 defaults,nofail 0 2"
    if ! grep -q "$volume_device_name" /etc/fstab; then
        echo "Updating /etc/fstab to make the mount persistent."
        echo \$FSTAB_ENTRY | sudo tee -a /etc/fstab
        else
        echo "The /etc/fstab already contains an entry for $volume_device_name."
    fi

    df -h $volume_mount_point
EOF