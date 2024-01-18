#!/bin/bash

if [ $# -lt 1 ]; then
    echo "Usage: $0 \"username/modelname\"."
    exit 1
fi

if [[ $1 =~ ^([^/]+)/([^/]+)$ ]]; then
    # Extract parts
    model_username="${BASH_REMATCH[1]}"
    modelname="${BASH_REMATCH[2]}"

    # Print extracted parts
    echo "Model Username: $model_username"
    echo "Model Name: $modelname"
else
    echo "Input string does not match the required format 'string1/string2'."
    exit 1
fi


source variables.sh

sql_server_private_ip=$(jq -r '.nodes[] | select(has("sql_server")) | .private_ip' config.json)
sql_server_database_password=$(jq -r '.nodes[] | select(has("sql_server")) | .sql_server.database_password' config.json)

web_ingress_private_ip=$(jq -r '.nodes[] | select(has("web_ingress")) | .private_ip' config.json)
web_ingress_public_ip=$(jq -r '.nodes[] | select(has("web_ingress")) | .web_ingress.public_ip' config.json)

node_ssh_username=$(jq -r '.ssh_username' config.json)
web_ingress_ssh_username=$(jq -r '.nodes[] | select(has("web_ingress")) | .web_ingress.ssh_username' config.json)

if [ $web_ingress_private_ip == $sql_server_private_ip ]; then
    sql_server_ssh_command="ssh -o StrictHostKeyChecking=no $web_ingress_ssh_username@$web_ingress_public_ip"
else
    sql_server_ssh_command="ssh -o StrictHostKeyChecking=no -J $web_ingress_ssh_username@$web_ingress_public_ip $node_ssh_username@$sql_server_private_ip"
fi


pg_conn_string="postgresql://modelbazaaruser:$sql_server_database_password@$sql_server_private_ip:5432/modelbazaar"

$sql_server_ssh_command <<EOF
set -e

if ! command -v psql &> /dev/null; then
    echo "psql could not be found. Installing postgresql-client..."
    sudo apt update
    sudo apt install postgresql-client -y
fi

user_id=\$(psql "$pg_conn_string" -At -c "select id from users where username='$model_username';")
if [ -z "\$user_id" ]; then
    echo "The user doesn't exist"
    exit
fi

model_id=\$(psql "$pg_conn_string" -At -c "select id from models where name='$modelname' and user_id='\$user_id';")
if [ -z "\$model_id" ]; then
    echo "The model doesn't exist."
    exit
fi

echo "Found model $1"
echo "Deleting resources associated with model $1..."

deployment_ids=(\$(psql "$pg_conn_string" -At -c "select id from deployments where model_id='\$model_id';"))
for deployment_id in \${deployment_ids[@]}; do
    echo "Deleting deployment deployment-\$deployment_id"
    curl -X DELETE "http://localhost:4646/v1/job/deployment-\$deployment_id"
done
psql "$pg_conn_string" -At -c "delete from models where name='$modelname' and user_id='\$user_id';"
rm -Rf /model_bazaar/models/\$model_id
rm -Rf $shared_dir/models/\$model_id
echo "Deleted resources associated with model $1"

EOF
