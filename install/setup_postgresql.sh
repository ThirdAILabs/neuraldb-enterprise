#!/bin/bash

PUBLIC_IPS=()

json=$(<config.json)

nodes=("HEADNODE_IP" "CLIENTNODE_IP")
for node in "${nodes[@]}"; do
    echo "$node"
    ips=($(echo $json | jq -r ".${node}[]"))
    for ip in "${ips[@]}"; do
        PUBLIC_IPS+=("$ip")
    done
done


PRIVATE_IPS=()

json=$(<config.json)

nodes=("PRIVATE_HEADNODE_IP" "PRIVATE_CLIENTNODE_IP")
for node in "${nodes[@]}"; do
    echo "$node"
    ips=($(echo $json | jq -r ".${node}[]"))
    for ip in "${ips[@]}"; do
        PRIVATE_IPS+=("$ip")
    done
done

# NFS Server Configuration
PUBLIC_SERVER_IP="${PUBLIC_IPS[0]}"
PRIVATE_SERVER_IP="${PRIVATE_IPS[0]}"


# Array of NFS Client IPs
PUBLIC_CLIENT_IPS=("${PUBLIC_IPS[@]:1}")
PRIVATE_CLIENT_IPS=("${PRIVATE_IPS[@]:1}")

# PostgreSQL Configuration
DATABASE_DIR=$database_dir
PASSWORD=$db_password

# SSH creds
USERNAME=$admin_name

ssh "$USERNAME"@$PUBLIC_SERVER_IP <<EOF
set -e

echo "$sudo_password" | sudo -S mkdir -p $DATABASE_DIR/docker-postgres-init
echo "$sudo_password" | sudo -S mkdir -p $DATABASE_DIR/data
cd $DATABASE_DIR/docker-postgres-init

echo "$sudo_password" | sudo -S tee init-db.sh > /dev/null <<'EOD'
#!/bin/bash
{
    echo "host  all all 172.17.0.0/16  md5"
    for IP in ${PRIVATE_CLIENT_IPS[@]}; do
        echo "host  all all \$IP/32  md5"
    done
} >> "\$PGDATA/pg_hba.conf"
EOD

echo "$sudo_password" | sudo -S chmod +x init-db.sh

echo "$sudo_password" | sudo -S docker pull postgres

echo "$sudo_password" | sudo -S docker stop neuraldb-enterprise-database || true
echo "$sudo_password" | sudo -S docker rm neuraldb-enterprise-database || true

echo "$sudo_password" | sudo -S docker run -d \
  --name neuraldb-enterprise-database \
  -e POSTGRES_PASSWORD=$PASSWORD \
  -e POSTGRES_DB=modelbazaar \
  -e POSTGRES_USER=modelbazaaruser \
  -v $DATABASE_DIR/docker-postgres-init:/docker-entrypoint-initdb.d \
  -v $DATABASE_DIR/data:/var/lib/postgresql/data \
  -p 5432:5432 \
  postgres

EOF