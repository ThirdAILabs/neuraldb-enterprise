#!/bin/bash

PUBLIC_NFS_IPS=()

json=$(<config.json)

nodes=("HEADNODE_IP" "CLIENTNODE_IP")
for node in "${nodes[@]}"; do
    echo "$node"
    ips=($(echo $json | jq -r ".${node}[]"))
    for ip in "${ips[@]}"; do
        PUBLIC_NFS_IPS+=("$ip")
    done
done


PRIVATE_NFS_IPS=()

json=$(<config.json)

nodes=("PRIVATE_HEADNODE_IP" "PRIVATE_CLIENTNODE_IP")
for node in "${nodes[@]}"; do
    echo "$node"
    ips=($(echo $json | jq -r ".${node}[]"))
    for ip in "${ips[@]}"; do
        PRIVATE_NFS_IPS+=("$ip")
    done
done

# NFS Server Configuration
PUBLIC_NFS_SERVER_IP="${PUBLIC_NFS_IPS[0]}"
PRIVATE_NFS_SERVER_IP="${PRIVATE_NFS_IPS[0]}"


# Array of NFS Client IPs
PUBLIC_NFS_CLIENT_IPS=("${PUBLIC_NFS_IPS[@]:1}")
PRIVATE_NFS_CLIENT_IPS=("${PRIVATE_NFS_IPS[@]:1}")

# PostgreSQL Configuration
PASSWORD=$db_password

# SSH creds
USERNAME=$admin_name

ssh "$USERNAME"@$PUBLIC_NFS_SERVER_IP <<EOF
# Update and install PostgreSQL
sudo apt update
sudo apt install -y postgresql postgresql-contrib
# Start and enable PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql
# Update PostgreSQL configuration
POSTGRESQL_DATA_DIR=\$(dirname "\$(sudo -u postgres psql -c "SHOW config_file;" -tA)")
sudo sed -i 's/#listen_addresses = '\''localhost'\''/listen_addresses = '\''*'\''/g' "\$POSTGRESQL_DATA_DIR/postgresql.conf"
# Configure pg_hba.conf to allow connections from cluster nodes
for IP in ${PRIVATE_NFS_CLIENT_IPS[@]}; do
    echo "host  all all \$IP/32  md5" | sudo tee -a "\$POSTGRESQL_DATA_DIR/pg_hba.conf"
done
# Restart PostgreSQL to apply the configuration
sudo systemctl restart postgresql
sudo systemctl enable postgresql
# Switch to the postgres user to create the database and user
sudo -i -u postgres
# Create a database
psql -c "CREATE DATABASE modelbazaar;"
# Create a user and grant privileges
psql -c "CREATE ROLE modelbazaaruser WITH LOGIN ENCRYPTED PASSWORD '$PASSWORD';"
psql -c "GRANT CONNECT ON DATABASE modelbazaar TO modelbazaaruser;"
psql -c "GRANT ALL PRIVILEGES ON DATABASE modelbazaar TO modelbazaaruser;"
# Exit the PostgreSQL shell and return to the user shell
exit
EOF

# Install postgresql client package on client nodes
for CLIENT_IP in "${PUBLIC_NFS_CLIENT_IPS[@]}"; do
    ssh "$USERNAME"@$CLIENT_IP <<EOF
sudo apt -y update
sudo apt install -y postgresql-client-common
sudo apt-get install -y postgresql-client
EOF
done



