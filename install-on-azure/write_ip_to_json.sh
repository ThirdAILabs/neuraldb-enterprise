#!/bin/bash

rm config.json
if [ ! -f "config.json" ]; then
  echo '{"HEADNODE_IP": [], "CLIENTNODE_IP": [], "PRIVATE_HEADNODE_IP": [], "PRIVATE_CLIENTNODE_IP": []}' > config.json
fi

# Fetch the HEAD node IP
PUBLIC_HEAD_IP=$(az vm list-ip-addresses --resource-group $resource_group_name --query "[?virtualMachine.name=='Head'].virtualMachine.network.publicIpAddresses[0].ipAddress" -o tsv)
jq --arg head_ip "$PUBLIC_HEAD_IP" '.HEADNODE_IP += [$head_ip]' config.json > temp.json && mv temp.json config.json

# Loop through client nodes to fetch their IPs
for ((i=1; i<=$vm_count; i++))
do
  CLIENT_NODE_IP=$(az vm list-ip-addresses --resource-group $resource_group_name --query "[?virtualMachine.name=='Node$i'].virtualMachine.network.publicIpAddresses[0].ipAddress" -o tsv)
  jq --arg client_ip "$CLIENT_NODE_IP" '.CLIENTNODE_IP += [$client_ip]' config.json > temp.json && mv temp.json config.json
done

# Fetch the HEAD node private IP
PRIVATE_HEAD_IP=$(az vm list-ip-addresses --resource-group $resource_group_name --query "[?virtualMachine.name=='Head'].virtualMachine.network.privateIpAddresses[0]" -o tsv)
jq --arg head_ip "$PRIVATE_HEAD_IP" '.PRIVATE_HEADNODE_IP += [$head_ip]' config.json > temp.json && mv temp.json config.json

# Loop through client nodes to fetch their private IPs
for ((i=1; i<=$vm_count; i++))
do
  PRIVATE_CLIENT_NODE_IP=$(az vm list-ip-addresses --resource-group $resource_group_name --query "[?virtualMachine.name=='Node$i'].virtualMachine.network.privateIpAddresses[0]" -o tsv)
  jq --arg client_ip "$PRIVATE_CLIENT_NODE_IP" '.PRIVATE_CLIENTNODE_IP += [$client_ip]' config.json > temp.json && mv temp.json config.json
done

# Adding the shared_disk logical unit number for mounting
jq --arg new_value $shared_disk_lun '.shared_disk_lun = $new_value' config.json > temp.json && mv temp.json config.json