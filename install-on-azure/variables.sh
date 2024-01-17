#!/bin/bash

# Should change these variables
resource_group_name="neuraldb-enterprise-group-kartik-4"
vnet_name="neuraldb-enterprise-vnet"
subnet_name="neuraldb-enterprise-subnet"
head_node_ipname="neuraldb-enterprise-ip"

# Can change these variables if desired
location="centralus"
vm_type="Standard_B4ms"
ssh_username="kartik"
vm_count=2  # vm_count must be greater than or equal to 0