#!/bin/bash

sql_server_private_ip=$(jq -r '.nodes[] | select(has("sql_server")) | .private_ip' config.json)
sql_server_database_dir=$(jq -r '.nodes[] | select(has("sql_server")) | .sql_server.database_dir' config.json)
sql_server_database_password=$(jq -r '.nodes[] | select(has("sql_server")) | .sql_server.database_password' config.json)
sql_client_private_ips=($(jq -r --arg ip "$sql_server_private_ip" '.nodes[] | select(.private_ip != $ip) | .private_ip' config.json))

sudo yum install postgresql15 -y
psql "postgresql://modelbazaaruser:${sql_server_database_password}@${sql_server_private_ip}:5432/modelbazaar" -c "delete from models where train_status != 'complete';"
psql "postgresql://modelbazaaruser:${sql_server_database_password}@${sql_server_private_ip}:5432/modelbazaar" -c "delete from deployments where status != 'complete';"

