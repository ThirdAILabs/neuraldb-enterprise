#!/bin/bash

sql_server_private_ip=$(jq -r '.nodes[] | select(has("sql_server")) | .private_ip' config.json)
sql_server_database_dir=$(jq -r '.nodes[] | select(has("sql_server")) | .sql_server.database_dir' config.json)
sql_server_database_password=$(jq -r '.nodes[] | select(has("sql_server")) | .sql_server.database_password' config.json)
sql_client_private_ips=($(jq -r --arg ip "$sql_server_private_ip" '.nodes[] | select(.private_ip != $ip) | .private_ip' config.json))


set -e

sudo mkdir -p $sql_server_database_dir/docker-postgres-init
sudo mkdir -p $sql_server_database_dir/data
cd $sql_server_database_dir/docker-postgres-init

sudo tee init-db.sh > /dev/null <<'EOD'
#!/bin/bash
{
    echo "host  all all 172.17.0.0/16  md5"
    for IP in ${sql_client_private_ips[@]}; do
        echo "host  all all $IP/32  md5"
    done
} >> "$PGDATA/pg_hba.conf"
EOD

sudo chmod +x init-db.sh

# sudo docker pull postgres

sudo docker stop neuraldb-enterprise-postgresql-server || true
sudo docker rm neuraldb-enterprise-postgresql-server || true

sudo docker run -d \
  --name neuraldb-enterprise-postgresql-server \
  -e POSTGRES_PASSWORD=$sql_server_database_password \
  -e POSTGRES_DB=modelbazaar \
  -e POSTGRES_USER=modelbazaaruser \
  -v $sql_server_database_dir/docker-postgres-init:/docker-entrypoint-initdb.d \
  -v $sql_server_database_dir/data:/var/lib/postgresql/data \
  -p 5432:5432 \
  postgres
