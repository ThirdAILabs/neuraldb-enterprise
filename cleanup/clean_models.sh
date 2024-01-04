#!/bin/bash

# This script cleans the models with the given status

if [ $# -lt 1 ] | [ $# -gt 2 ]; then
    echo "$0 <status> <model_id>"
    echo "status: not_started | starting | in_progress | stopping | complete | failed"
    echo "model_id. Default: all with the given status"
    exit 1
fi

options=("not_started" "starting" "in_progress" "stopping" "complete" "failed")


if [[ " ${options[@]} " =~ " $1 " ]]; then
    status=$1
else
    echo "provide a valid status: not_started | starting | in_progress | stopping | complete | failed"
    exit 1
fi

if [ $# -eq 2 ]; then
    model_id=$2
fi


source variables.sh

PUBLIC_SERVER_IP="$(jq -r '.HEADNODE_IP | .[0]' config.json)"
PRIVATE_SERVER_IP="$(jq -r '.PRIVATE_HEADNODE_IP | .[0]' config.json)"

PASSWORD=$db_password
USERNAME=$admin_name
PG_CONN_STRING="postgresql://modelbazaaruser:$PASSWORD@$PRIVATE_SERVER_IP:5432/modelbazaar"

ssh "$USERNAME"@$PUBLIC_SERVER_IP << EOF

cleanup_dir="$shared_dir/clean_up"
mkdir \$cleanup_dir 2>/dev/null

sudo tee \$cleanup_dir/clean_models.sh > /dev/null <<'EOD'
#!/bin/bash
set -e

if ! command -v psql &> /dev/null; then
    echo "psql could not be found. Installing postgresql-client..."
    sudo apt update
    sudo apt install postgresql-client -y
fi

# fetching the records
if [ -n "$model_id" ]; then
    query="select id from models where train_status='$status' and id='$model_id';"
    result=(\$(psql "$PG_CONN_STRING" -At -c "\$query"))

    if [ -z "\$result" ]; then
        echo "No deployment exists with status $status and deployment id: $model_id"
        exit 1
    fi
else
    echo -n "Are you sure to delete all models with status $status? (y/n)"
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
                echo -n "Invalid choice. Please enter 'y' or 'n'."
                ;;
        esac
    done
    
    query="select id from models where train_status='$status';"
    result=(\$(psql "$PG_CONN_STRING" -At -c "\$query"))
fi

for model_id in "\${result[@]}"; do
    # Removing the deployements of the model with model_id
    deployment_ids=(\$(psql "$PG_CONN_STRING" -At -c "select id from deployments where model_id='\$model_id';"))
    for deployment_id in \${deployment_ids[@]}; do
        echo -n "Delete model's deployment with id: \$deployment_id (Y/y). Anything else will skip this one."
        read response
        if [[ "\$response" =~ ^[Yy]$ ]]; then
            curl --silent -X DELETE http://$PUBLIC_SERVER_IP:4646/v1/job/deployment-\$deployment_id?purge=true
        fi
        
    done

    echo "Removing model with id: \$model_id"
    psql "$PG_CONN_STRING" -c "Delete from models where id='\$model_id';" > /dev/null

    # Stop and purge nomad job
    job_name="train-\$model_id"
    curl --silent -X DELETE http://$PUBLIC_SERVER_IP:4646/v1/job/\$job_name?purge=true

    rm -rf $shared_dir/models/\$model_id
done

EOD
EOF

echo "Follow these setps: "
echo "1. Login to the head node: ssh $USERNAME@$PUBLIC_SERVER_IP"
echo "2. Navigate to the directory: $shared_dir/clean_up"
echo "3. Run the command: source clean_models.sh"