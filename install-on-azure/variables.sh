#!/bin/bash

# Should change these variables
resource_group_name="Gautam-external-drive-nfs-rg"
vnet_name="Gautam-external-drive-nfs-vnet"
subnet_name="Gautam-external-drive-nfs-subnet"
head_node_ipname="Gautam-external-drive-nfs-ip"
admin_name="gautam"
vm_name="Head"
disk_name="DataDisk"

# Can change these variables if desired
location="centralus"
vm_type="Standard_DS2_v2"
vm_count=3  # vm_count must be greater than or equal to 0

# provide the path of the custom shared drive
# shared_dir="/path/to/shared/dir"