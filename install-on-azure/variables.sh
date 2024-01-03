#!/bin/bash

# Should change these variables
resource_group_name="neuraldb-enterprise-group-gautam"
vnet_name="neuraldb-enterprise-vnet-gautam"
subnet_name="neuraldb-enterprise-subnet-gautam"
head_node_ipname="neuraldb-enterprise-ip-gautam"
admin_name="admingautam"

# Can change these variables if desired
location="centralus"
vm_type="Standard_DS2_v2"
vm_count=2  # vm_count must be greater than or equal to 0