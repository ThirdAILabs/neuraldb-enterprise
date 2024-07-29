#!/bin/bash

project_name="neuraldb-enterprise"

# Key pair for SSHing into instances
key_name="neuraldb-enterprise-key"
public_key_path="~/.ssh/id_rsa.pub"  # Change this to point to your machine's public key

# VPC/Subnet setup
region="us-east-1"
vpc_cidr_block="192.168.0.0/16"
availability_zone="us-east-1d"
subnet_cidr_block="192.168.0.0/24"

# Instances
instance_type="t2.xlarge"
vm_count=1  # vm_count must be greater than or equal to 0

# Volume
# If 'existing_volume_id' is the empty string, create_vms.sh will create a new volume and mount
# that to the head node. If 'existing_volume_id' points to an existing volume, then that will be
# mounted onto the head node instead.
existing_volume_id=""  
volume_device_name="/dev/xvdf"
volume_mount_point="/opt/neuraldb_enterprise"
volume_size="64"
volume_type="gp2"