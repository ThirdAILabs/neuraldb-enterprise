#!/bin/bash

PUBLIC_IPS=()

json=$(<config.json)

nodes=("HEADNODE_IP")
for node in "${nodes[@]}"; do
    echo "$node"
    ips=($(echo $json | jq -r ".${node}[]"))
    for ip in "${ips[@]}"; do
        PUBLIC_IPS+=("$ip")
    done
done


PRIVATE_IPS=()

json=$(<config.json)

nodes=("PRIVATE_CLIENTNODE_IP")
for node in "${nodes[@]}"; do
    echo "$node"
    ips=($(echo $json | jq -r ".${node}[]"))
    for ip in "${ips[@]}"; do
        PRIVATE_IPS+=("$ip")
    done
done

# NFS Server Configuration
PUBLIC_SERVER_IP="${PUBLIC_IPS[0]}"

NFS_CLIENT=$(jq -r '.NFS_CLIENT_IP[0]' config.json)

# PostgreSQL Configuration
DATABASE_DIR=$database_dir
PASSWORD=$db_password

# SSH creds
USERNAME=$admin_name
NODEPASSD=$node_password

env SSHPASS="$NODEPASSD" sshpass -d 123 ssh -o ProxyCommand="sshpass -e ssh -W %h:%p $USERNAME@$PUBLIC_SERVER_IP" $USERNAME@$NFS_CLIENT 123<<<$NODEPASSD <<EOF
set -e

sudo mkdir -p $DATABASE_DIR/docker-postgres-init
sudo mkdir -p $DATABASE_DIR/data
cd $DATABASE_DIR/docker-postgres-init

sudo tee init-db.sh > /dev/null <<'EOD'
#!/bin/bash
{
    echo "host  all all 172.17.0.0/16  md5"
    for IP in ${PRIVATE_IPS[@]}; do
        echo "host  all all \$IP/32  md5"
    done
} >> "\$PGDATA/pg_hba.conf"
EOD

sudo chmod +x init-db.sh

sudo docker pull postgres

sudo docker stop neuraldb-enterprise-database || true
sudo docker rm neuraldb-enterprise-database || true

sudo docker run -d \
  --name neuraldb-enterprise-database \
  -e POSTGRES_PASSWORD=$PASSWORD \
  -e POSTGRES_DB=modelbazaar \
  -e POSTGRES_USER=modelbazaaruser \
  -v $DATABASE_DIR/docker-postgres-init:/docker-entrypoint-initdb.d \
  -v $DATABASE_DIR/data:/var/lib/postgresql/data \
  -p 5432:5432 \
  postgres

EOF