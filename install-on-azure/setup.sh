#!/bin/bash

# This creates $vm_count + 1 VMs as of now. The first one is the head node that has 1024GBs of disk space and the PRIVATE IP of the VM inside the subnet has been hardcoded to 10.0.0.4
# We create a Virtual Network and a subnet inside this script and add rules to NICs of the VMs created.
bash create_vms.sh

# This writes files in config.json
# Basically this a programmatic way of writing all the IP addresses of the VMs that we have created into a JSON File
bash write_ip_to_json.sh

# This mounts the shared disk drive on the headnode
bash mount_disk.sh