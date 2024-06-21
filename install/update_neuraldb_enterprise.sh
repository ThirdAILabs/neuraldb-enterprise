#!/bin/bash

source variables.sh


web_ingress_public_ip=$(jq -r '.nodes[] | select(has("web_ingress")) | .web_ingress.public_ip' config.json)
web_ingress_private_ip=$(jq -r '.nodes[] | select(has("web_ingress")) | .private_ip' config.json)

web_ingress_ssh_username=$(jq -r '.nodes[] | select(has("web_ingress")) | .web_ingress.ssh_username' config.json)
node_ssh_username=$(jq -r '.ssh_username' config.json)

nomad_server_private_ip=$(jq -r '.nodes[] | select(has("nomad_server")) | .private_ip' config.json)

self_hosted_sql_server=$(jq -r 'any(.nodes[]; has("sql_server"))' config.json)
if [ "$self_hosted_sql_server" = true ]; then
    sql_server_database_password=$(jq -r '.nodes[] | select(has("sql_server")) | .sql_server.database_password' config.json)
    sql_server_private_ip=$(jq -r '.nodes[] | select(has("sql_server")) | .private_ip' config.json)
    sql_uri="postgresql://modelbazaaruser:${sql_server_database_password}@${sql_server_private_ip}:5432/modelbazaar"
else
    sql_uri=$(jq -r '.sql_uri' config.json)
fi

shared_dir=$(jq -r '.nodes[] | select(has("shared_file_system")) | .shared_file_system.shared_dir' config.json)

if [ $web_ingress_private_ip == $nomad_server_private_ip ]; then
    nomad_server_ssh_command="ssh -o StrictHostKeyChecking=no $web_ingress_ssh_username@$web_ingress_public_ip"
else
    nomad_server_ssh_command="ssh -o StrictHostKeyChecking=no -J $web_ingress_ssh_username@$web_ingress_public_ip $node_ssh_username@$nomad_server_private_ip"
fi

acl_token=$($nomad_server_ssh_command "grep 'Secret ID' \"/opt/neuraldb_enterprise/nomad_data/task_runner_token.txt\" | awk '{print \$NF}'")


# TODO: SSH into the nomad server node and launch/delete the jobs locally.

delete_model_bazaar_url="http://${web_ingress_public_ip}:4646/v1/job/modelbazaar"
delete_search_ui_url="http://${web_ingress_public_ip}:4646/v1/job/search-ui"

curl -s -X DELETE -H "X-Nomad-Token: $acl_token" "$delete_model_bazaar_url"
curl -s -X DELETE -H "X-Nomad-Token: $acl_token" "$delete_search_ui_url"

bash ../nomad/nomad_jobs/submit_nomad_job.sh "$nomad_server_ssh_command" ../nomad/nomad_jobs/model_bazaar_job.hcl.tpl $acl_token SQL_URI=$sql_uri SHARE_DIR=$shared_dir PUBLIC_SERVER_IP=$web_ingress_public_ip PRIVATE_SERVER_IP=$nomad_server_private_ip JWT_SECRET=$jwt_secret ADMIN_USERNAME=$admin_username ADMIN_MAIL=$admin_mail ADMIN_PASSWORD=$admin_password AUTOSCALING_ENABLED=$autoscaling_enabled AUTOSCALER_MAX_COUNT=$autoscaler_max_count GENAI_KEY=$genai_key
