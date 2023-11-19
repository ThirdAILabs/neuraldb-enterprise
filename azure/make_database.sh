echo "Creating a flexible Postgres DB Server $db_server_name"

az postgres flexible-server create \
  --resource-group $resource_group_name \
  --name $db_server_name \
  --location $location \
  --admin-user $db_admin_username \
  --admin-password $db_admin_password \
  --sku-name Standard_D2s_v3 \
  --version 14 \
  --yes

echo "Creating a db $db_name inside the server"
az postgres flexible-server db create \
  --resource-group $resource_group_name \
  --database-name $db_name \
  --server-name $db_server_name 

echo "Exposing the db to the world"
az postgres flexible-server firewall-rule create \
    --resource-group $resource_group_name \
    --name $db_server_name \
    --rule-name "allowAllThirdAIDB" \
    --start-ip-address 0.0.0.0 \
    --end-ip-address 255.255.255.255


echo "Finding the DB host"

export server_details=$(az postgres flexible-server show \
  --resource-group $resource_group_name \
  --name $db_server_name --query "fullyQualifiedDomainName" -o tsv)

export DB_URI="postgresql://$db_admin_username:$db_admin_password@$server_details:5432/$db_name?sslmode=require"