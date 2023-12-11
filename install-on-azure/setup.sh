#!/bin/bash

# This just loads the resource group variables.
source variables.sh

# This creates $vm_count VMs as of now. The first one is the head node that has 100GBs of disk space and the PRIVATE IP of the VM inside the subnet has been hardcoded to 10.0.0.4
# We create a Virtual Network and a subnet inside this script and add rules to NICs of the VMs created.
source create_vms.sh

# This writes files in config.json
# Basically this a programmatic way of writing all the public IP addresses of the VMs that we have created into a JSON File
source write_ip_to_json.sh