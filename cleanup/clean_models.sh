#!/bin/bash

# This script cleans the models with the given status

if [ $# -lt 1 ] | [ $# -gt 2 ]; then
    echo "$0 <status> <model_id>"
    echo "status: not_started | starting | in_progress | stopping | complete | failed"
    echo "model_id. Default: all with the given status"
    exit 1
fi

status=$1
if [ $# -eq 2 ]; then
    model_id=$2
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

# fetching the records
if [ -n "$model_id" ]; then
    query="select id from models where train_status='$status' and id='$model_id'"
    result=\$(psql "$PG_CONN_STRING" -At -c "\$query")

    if [ -z "\$temp_id" ]; then
        echo "No deployment exists with status $status and deployment id: $model_id"
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

    query="select id from models where train_status='$status'"
    result=\$(psql "$PG_CONN_STRING" -At -c "\$query")
fi

for model_id in "${\result[@]}"; do
    echo "Removing deployment with id: \$model_id"
    psql "$PG_CONN_STRING" -At -c "Delete from models where id=\$model_id"

    # Stop and purge nomad job
    job_name="deployment-\$model_id"
    curl --silent -X DELETE http://$PUBLIC_SERVER_IP:4646/v1/job/\$job_name?purge=true

    rm -rf $shared_dir/models/\$model_id
done


EOF