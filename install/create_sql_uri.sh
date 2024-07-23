#!/bin/bash

nomad_data_dir=/opt/neuraldb_enterprise/nomad_data

web_ingress_private_ip=$(jq -r '.nodes[] | select(has("web_ingress")) | .private_ip' config.json)
web_ingress_public_ip=$(jq -r '.nodes[] | select(has("web_ingress")) | .web_ingress.public_ip' config.json)

node_ssh_username=$(jq -r '.ssh_username' config.json)
web_ingress_ssh_username=$(jq -r '.nodes[] | select(has("web_ingress")) | .web_ingress.ssh_username' config.json)

nomad_server_private_ip=$(jq -r '.nodes[] | select(has("nomad_server")) | .private_ip' config.json)

if [ $web_ingress_private_ip == $nomad_server_private_ip ]; then
    nomad_server_ssh_command="ssh -o StrictHostKeyChecking=no $web_ingress_ssh_username@$web_ingress_public_ip"
else
    nomad_server_ssh_command="ssh -o StrictHostKeyChecking=no -J $web_ingress_ssh_username@$web_ingress_public_ip $node_ssh_username@$nomad_server_private_ip"
fi

self_hosted_sql_server=$(jq -r 'any(.nodes[]; has("sql_server"))' config.json)
if [ "$self_hosted_sql_server" = true ]; then
    sql_server_database_password=$(jq -r '.nodes[] | select(has("sql_server")) | .sql_server.database_password' config.json)
    sql_server_private_ip=$(jq -r '.nodes[] | select(has("sql_server")) | .private_ip' config.json)
    sql_uri="postgresql://modelbazaaruser:${sql_server_database_password}@${sql_server_private_ip}:5432/modelbazaar"
else
    sql_uri=$(jq -r '.sql_uri' config.json)
    if [ "$sql_uri" = "ENV" ]; then
        $nomad_server_ssh_command <<EOF
            management_token=\$(grep 'Secret ID' "$nomad_data_dir/management_token.txt"  | awk '{print \$NF}')
            nomad var get -namespace default -token "\$management_token" nomad/jobs | nomad var put -namespace default -token "\$management_token" -in=json -out=table - sql_uri=postgresql://\${DB_USERNAME}:\${DB_PASSWORD}@\${DB_HOSTNAME}:5432/\${DB_NAME} > /dev/null
EOF
        exit 0
    fi
fi

$nomad_server_ssh_command <<EOF
    management_token=\$(grep 'Secret ID' "$nomad_data_dir/management_token.txt"  | awk '{print \$NF}')
    nomad var get -namespace default -token "\$management_token" nomad/jobs | nomad var put -namespace default -token "\$management_token" -in=json -out=table - sql_uri=$sql_uri > /dev/null
EOF



