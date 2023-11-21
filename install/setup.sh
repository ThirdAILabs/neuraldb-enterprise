# This just loads the resource group variables.
source variables.sh

# Set up the NFS server on the Head node, and mount the NFS server on each of the clients
source setup_nfs.sh

# Upload the Rag on Rails license to the Nomad cluster
source upload_license.sh

# Set up the PostgreSQL server on the Head node, and install the PostgreSQL client on the client nodes
source setup_postgresql.sh

# Once we have written the IPs of the VMs to the json files, there are two things left to be done
# 1. Setup Nomad on each of the nodes
# 2. Setup server, client, and the proxy_server

source run_nomad_scripts.sh server
source run_nomad_scripts.sh proxy_server
source run_nomad_scripts.sh client

# Now we can launch the Model Bazaar jobs onto our nomad cluster 
source launch_nomad_jobs.sh