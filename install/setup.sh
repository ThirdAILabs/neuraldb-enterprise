#!/bin/bash

# Exactly one of 'sql_server' and 'sql_uri' must be specified
self_hosted_sql_server=$(jq -r 'any(.nodes[]; has("sql_server"))' config.json)
external_hosted_sql_server=$(jq -r 'has("sql_uri")' config.json)
if { [ "$self_hosted_sql_server" == true ] && [ "$external_hosted_sql_server" == true ]; } || { [ "$self_hosted_sql_server" == false ] && [ "$external_hosted_sql_server" == false ]; }; then
    echo "Error: Exactly one of sql_server and sql_uri must be supplied in config.json."
    exit 1
fi

# Set up the NFS server on the Head node, and mount the NFS server on each of the clients
# bash setup_nfs.sh

# Check if the shared dir collaboration is working properly or not
( bash shared_disk_check.sh )
if [ $? -ne 0 ]; then
    echo "Error: Directory is not being shared among nodes. Ensure that all nodes have access to the shared directory before rerunning this script"
else
    # Upload the Rag on Rails license to the Nomad cluster
    # bash upload_license.sh

    # # Launch the Nomad Server and Clients
    # bash setup_nomad.sh

    # Set up the PostgreSQL server on the Head node, and install the PostgreSQL client on the client nodes
    self_hosted_sql_server=$(jq -r 'any(.nodes[]; has("sql_server"))' config.json)
    if [ "$self_hosted_sql_server" = true ]; then
        bash setup_postgresql.sh
    fi

    # Now we can launch the Model Bazaar jobs onto our nomad cluster 
    bash launch_nomad_jobs.sh
fi
