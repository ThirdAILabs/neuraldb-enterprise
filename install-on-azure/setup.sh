# This just loads the resource group variables.
source variables.sh

# This creates $vm_count VMs as of now. The first one is the head node that has 100GBs of disk space and the PRIVATE IP of the VM inside the subnet has been hardcoded to 10.0.0.4
# We create a Virtual Network and a subnet inside this script and add rules to NICs of the VMs created.
source create_vms.sh

# This writes files in config.json
# Basically this a programmatic way of writing all the public IP addresses of the VMs that we have created into a JSON File
source write_ip_to_json.sh

# Set up the NFS server on the Head node, and mount the NFS server on each of the clients
source setup_nfs.sh

# Upload the Rag on Rails license to the Nomad cluster
source upload_license.sh

# Set up the PostgreSQL server on the Head node, and install the PostgreSQL client on the client nodes
source setup_postgresql.sh

# Once we have written the IPs of the VMs to the json files, there are two things left to be done
# 1. Setup Nomad on each of the nodes
# 2. Setup server and clients

source run_nomad_scripts.sh server
source run_nomad_scripts.sh client

# Now we can launch the Model Bazaar jobs onto our nomad cluster 
source launch_nomad_jobs.sh