#!/bin/bash

# Creates a resource group
echo "Creating a resource group with the name $resource_group_name..."
az group create --location $location --name $resource_group_name

# Create a VNET so that we can control the Private IP of the Head Node VM
az network vnet create \
  --name $vnet_name \
  --resource-group $resource_group_name \
  --location $location \
  --address-prefix 10.0.0.0/16

# We add a subnet. The NIC of the VM created will attach to this subnet
az network vnet subnet create \
  --name $subnet_name \
  --resource-group $resource_group_name \
  --vnet-name $vnet_name \
  --address-prefixes 10.0.0.0/24

# When we attach a network interface card to a VM, the Public IP of the VM is not automatically commissioned. Hence, we have to explicitly create a Public IP
az network public-ip create \
  --name $head_node_ipname \
  --resource-group $resource_group_name \
  --location $location \
  --allocation-method Static

# Once we have created a Public IP, we create an NIC to which we attach the Public IP Address
az network nic create \
  --name NomadHeadNic \
  --resource-group $resource_group_name \
  --vnet-name $vnet_name \
  --subnet $subnet_name \
  --private-ip-address 10.0.0.4 \
  --public-ip-address $head_node_ipname

# This created the Head Node of the VM. In the future we can support more things like specifying VM sizes or the Data Disk Size.
az vm create \
  --name Head \
  --resource-group $resource_group_name \
  --location $location \
  --image Ubuntu2204 \
  --nics NomadHeadNic \
  --admin-username $admin_name \
  --generate-ssh-keys \
  --size $vm_type \
  --data-disk-sizes-gb 100

# These creates Client Nodes.
for ((i=1; i<=$vm_count; i++))
do
  az vm create \
    --resource-group $resource_group_name \
    --name Node$i \
    --image Ubuntu2204 \
    --admin-username $admin_name \
    --generate-ssh-keys \
    --size $vm_type
done


# We first add rules so that any VM that we have created become a part of a Virtual Network can access each other on any port. 
# Note that we have opened all the ports to all traffics through public IP addresses. This is generally a bad thing.
# TODO : Change the above to only open specific ports

# This is where we create a network security group that allows all traffic from all ports and addresses inside the virtual network firewall bypassable.
az network nsg create --resource-group $resource_group_name --name allowall

az network nsg rule create --resource-group $resource_group_name --nsg-name allowall --name AllowAllInbound --priority 100 --source-address-prefixes VirtualNetwork --destination-address-prefixes VirtualNetwork --access Allow --protocol '*' --direction Inbound

az network nsg rule create --resource-group $resource_group_name --nsg-name allowall --name AllowAllOutbound --priority 100 --source-address-prefixes VirtualNetwork --destination-address-prefixes VirtualNetwork --access Allow --protocol '*' --direction Outbound

# This rule is added to allow SSH traffic from outside world to access the VMs.
az network nsg rule create --resource-group $resource_group_name --nsg-name allowall --name AllowSSH --priority 110 --source-address-prefixes '*' --destination-address-prefixes '*' --access Allow --protocol Tcp --destination-port-ranges 22 --direction Inbound

az network nsg rule create --resource-group $resource_group_name --nsg-name allowall --name AllowAllInbound --priority 120 --source-address-prefixes '*' --source-port-ranges '*' --destination-address-prefixes '*' --destination-port-ranges '*' --access Allow --protocol '*' --direction Inbound

az network nsg rule create --resource-group $resource_group_name --nsg-name allowall --name AllowAllOutbound --priority 130 --source-address-prefixes '*' --source-port-ranges '*' --destination-address-prefixes '*' --destination-port-ranges '*' --access Allow --protocol '*' --direction Outbound

# Finally, we add all the VMs that we have created to this Network Inferface (basically applying security policies)
az network nic update --resource-group $resource_group_name --name NomadHeadNic --network-security-group allowall

for ((i=1; i<=$vm_count; i++))
do
  az network nic update --resource-group $resource_group_name --name Node${i}VMNic --network-security-group allowall
done