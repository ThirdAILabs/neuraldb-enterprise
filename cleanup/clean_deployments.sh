#!/bin/bash

# This script cleans the deployments with the given status

if [ $# -lt 1 ] | [ $# -gt 2 ]; then
    echo "$0 <status> <deployment_id>"
    echo "status: not_started | starting | in_progress | stopping | complete | failed"
    echo "deployment_id. Default: all with the given status"
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
    deployment_id=$2
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

sudo tee \$cleanup_dir/clean_deployments.sh > /dev/null <<'EOD'
#!/bin/bash
set -e

if ! command -v psql &> /dev/null; then
    echo "psql could not be found. Installing postgresql-client..."
    sudo apt update
    sudo apt install postgresql-client -y
fi

# fetching the records
if [ -n "$deployment_id" ]; then
    query="select id from deployments where status='$status' and id='$deployment_id';"
    result=(\$(psql "$PG_CONN_STRING" -At -c "\$query"))

    if [ -z "\$result" ]; then
        echo "No deployment exists with status $status and deployment id: $deployment_id"
        exit 1
    fi
else
    echo -n "Are you sure to delete all deployments with status $status? (y/n)"
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
    
    query="select id from deployments where status='$status';"
    result=(\$(psql "$PG_CONN_STRING" -At -c "\$query"))
fi

for deployment_id in "\${result[@]}"; do
    # Removing the deployment
    echo -n "Delete deployment with id: \$deployment_id (Y/y). Anything else will skip this one."
    read response
    if [[ "\$response" =~ ^[Yy]$ ]]; then
        curl --silent -X DELETE http://$PUBLIC_SERVER_IP:4646/v1/job/deployment-\$deployment_id?purge=true
    fi

    psql "$PG_CONN_STRING" -c "Delete from deployments where id='\$deployment_id';" > /dev/null

done

EOD
EOF

echo "Follow these setps: "
echo "1. Login to the head node: ssh $USERNAME@$PUBLIC_SERVER_IP"
echo "2. Navigate to the directory: $shared_dir/clean_up"
echo "3. Run the command: source clean_deployments.sh"