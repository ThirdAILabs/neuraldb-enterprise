#!/bin/bash

# cleaning the database 
source variables.sh


PUBLIC_SERVER_IP="$(jq -r '.HEADNODE_IP | .[0]' config.json)"
PRIVATE_SERVER_IP="$(jq -r '.PRIVATE_HEADNODE_IP | .[0]' config.json)"

PASSWORD=$db_password
USERNAME=$admin_name
PG_CONN_STRING="postgresql://modelbazaaruser:$PASSWORD@$PRIVATE_SERVER_IP:5432/modelbazaar"


ssh "$USERNAME"@$PUBLIC_SERVER_IP <<EOF
tables=(\$(psql "$PG_CONN_STRING" -At -c "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';"))
for table in "\${tables[@]}"; do 
    psql "$PG_CONN_STRING" -c "TRUNCATE TABLE \$table CASCADE;"
done
EOF

# Cleaning the nfs directory
ssh "$USERNAME"@$PUBLIC_SERVER_IP <<EOF
rm -rf $shared_dir/data/*
rm -rf $shared_dir/models/*
rm -rf $shared_dir/users/*
EOF

# Stopping and purging nomad jobs
jobs=($(curl -s http://$PUBLIC_SERVER_IP:4646/v1/jobs | jq -r '.[].Name'))
for job in "${jobs[@]}"; do
    echo $job
    curl -s -X DELETE http://$PUBLIC_SERVER_IP:4646/v1/job/$job?purge=true
done

# Restarting the nomad client and server jobs
source ../install/run_nomad_scripts.sh server
source ../install/run_nomad_scripts.sh client

# Now we can launch the Model Bazaar jobs onto our nomad cluster 
source ../install/launch_nomad_jobs.sh