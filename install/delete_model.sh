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

PUBLIC_IPS=()

json=$(<config.json)

nodes=("HEADNODE_IP" "CLIENTNODE_IP")
for node in "${nodes[@]}"; do
    ips=($(echo $json | jq -r ".${node}[]"))
    for ip in "${ips[@]}"; do
        PUBLIC_IPS+=("$ip")
    done
done


PRIVATE_IPS=()

json=$(<config.json)

nodes=("PRIVATE_HEADNODE_IP" "PRIVATE_CLIENTNODE_IP")
for node in "${nodes[@]}"; do
    ips=($(echo $json | jq -r ".${node}[]"))
    for ip in "${ips[@]}"; do
        PRIVATE_IPS+=("$ip")
    done
done

# NFS Server Configuration
PUBLIC_SERVER_IP="${PUBLIC_IPS[0]}"
PRIVATE_SERVER_IP="${PRIVATE_IPS[0]}"


# Array of NFS Client IPs
PUBLIC_CLIENT_IPS=("${PUBLIC_IPS[@]:1}")
PRIVATE_CLIENT_IPS=("${PRIVATE_IPS[@]:1}")

PASSWORD=$db_password
USERNAME=$admin_name
PG_CONN_STRING="postgresql://modelbazaaruser:$PASSWORD@$PRIVATE_SERVER_IP:5432/modelbazaar"

ssh "$USERNAME"@$PUBLIC_SERVER_IP <<EOF
set -e

if ! command -v psql &> /dev/null; then
    echo "psql could not be found. Installing postgresql-client..."
    sudo apt update
    sudo apt install postgresql-client -y
fi

user_id=\$(psql "$PG_CONN_STRING" -At -c "select id from users where username='$model_username';")
if [ -z "\$user_id" ]; then
    echo "The user doesn't exist"
    exit
fi

model_id=\$(psql "$PG_CONN_STRING" -At -c "select id from models where name='$modelname' and user_id='\$user_id';")
if [ -z "\$model_id" ]; then
    echo "The model doesn't exist."
    exit
fi

echo "Found model $1"
echo "Deleting resources associated with model $1..."

deployment_ids=(\$(psql "$PG_CONN_STRING" -At -c "select id from deployments where model_id='\$model_id';"))
for deployment_id in \${deployment_ids[@]}; do
    echo "Deleting deployment deployment-\$deployment_id"
    curl -X DELETE "http://localhost:4646/v1/job/deployment-\$deployment_id"
done
psql "$PG_CONN_STRING" -At -c "delete from models where name='$modelname' and user_id='\$user_id';"
rm -Rf /model_bazaar/models/\$model_id
rm -Rf $shared_dir/models/\$model_id
echo "Deleted resources associated with model $1"

EOF
