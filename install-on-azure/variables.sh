#!/bin/bash

# Should change these variables
resource_group_name="neuraldb-enterprise-group"
vnet_name="neuraldb-enterprise-vnet"
subnet_name="neuraldb-enterprise-subnet"
head_node_ipname="neuraldb-enterprise-ip"
admin_name="admin"

# Can change these variables if desired
location="centralus"
vm_type="Standard_DS2_v2"
vm_count=2  # vm_count must be greater than or equal to 0

# provide the path of the custom shared drive
# custom_shared_dir="/path/to/shared/dir"