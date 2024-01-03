#!/bin/bash

# This script cleans the deployments with the given status

if [ $# -lt 1 ] | [ $# -gt 2 ]; then
    echo "$0 <status> <deployment_id>"
    echo "status: not_started | starting | in_progress | stopping | complete | failed"
    echo "deployment_id. Default: all with given status"
    exit 1
fi

status=$1
if [ $# -eq 2 ]; then
    deployment_id=$2
fi

source variables.sh

PUBLIC_SERVER_IP="$(jq -r '.HEADNODE_IP | .[0]' config.json)"
PRIVATE_SERVER_IP="$(jq -r '.PRIVATE_HEADNODE_IP | .[0]' config.json)"

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

# fetching the deployments
if [ -n "$deployment_id" ]; then
    query="select id from deployments where status='$status' and id='$deployment_id'"
    result=\$(psql "$PG_CONN_STRING" -At -c "\$query")

    if [ -z "\$temp_id" ]; then
        echo "No deployment exists with the deployment id: $deployment_id"
        exit 1
    fi
else
    echo "Are you sure to delete all models with status $status? (y/n)"
    while true; do
        read answer
        case "\$answer" in
            [Yy])
                break
                ;;
            [Nn])
                echo "exiting..."
                exit 1
                ;;
            *)
                echo "Invalid choice. Please enter 'y' or 'n'."
                ;;
    done
    query="select id from deployments where status='$status'"
    result=\$(psql "$PG_CONN_STRING" -At -c "\$query")
fi

for deployment_id in "${\result[@]}"; do
    echo "Removing deployment with id: \$deployment_id"
    psql "$PG_CONN_STRING" -At -c "Delete from deployments where id=\$deployment_id"

    # Stop and purge nomad job
    job_name="deployment-\$deployment_id"

    curl --silent -X DELETE http://$PUBLIC_SERVER_IP:4646/v1/job/\$job_name?purge=true
done
EOF