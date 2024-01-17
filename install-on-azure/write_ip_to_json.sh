#!/bin/bash

source variables.sh

rm config.json
if [ ! -f "config.json" ]; then
  echo "{
  \"nodes\": [
    {
      \"private_ip\": \"\",
      \"web_ingress\": {
        \"public_ip\": \"\",
        \"run_jobs\": true,
        \"ssh_username\": \"$ssh_username\"
      },
      \"sql_server\": {
        \"database_dir\": \"/opt/neuraldb_enterprise/database\",
        \"database_password\": \"password\"
      },
      \"shared_file_system\": {
        \"create_nfs_server\": true,
        \"shared_dir\": \"/opt/neuraldb_enterprise/model_bazaar\"
      },
      \"nomad_server\": true
    }
  ],
  \"ssh_username\": \"$ssh_username\"
}" > config.json
fi

# Fetch the HEAD node IP
web_ingress_public_ip=$(az vm list-ip-addresses --resource-group $resource_group_name --query "[?virtualMachine.name=='Head'].virtualMachine.network.publicIpAddresses[0].ipAddress" -o tsv)
jq --arg public_ip "$web_ingress_public_ip" '.nodes |= map(if has("web_ingress") then .web_ingress.public_ip = $public_ip else . end)' config.json > temp.json && mv temp.json config.json

# # Fetch the HEAD node private IP
web_ingress_private_ip=$(az vm list-ip-addresses --resource-group $resource_group_name --query "[?virtualMachine.name=='Head'].virtualMachine.network.privateIpAddresses[0]" -o tsv)
jq --arg private_ip "$web_ingress_private_ip" '.nodes |= map(if has("web_ingress") then .private_ip = $private_ip else . end)' config.json > temp.json && mv temp.json config.json

# Loop through client nodes to fetch their private IPs
for ((i=1; i<=$vm_count; i++))
do
  client_node_private_ip=$(az vm list-ip-addresses --resource-group $resource_group_name --query "[?virtualMachine.name=='Node$i'].virtualMachine.network.privateIpAddresses[0]" -o tsv)
  jq --arg private_ip "$client_node_private_ip" '.nodes += [{"private_ip": $private_ip}]' config.json > temp.json && mv temp.json config.json
done
