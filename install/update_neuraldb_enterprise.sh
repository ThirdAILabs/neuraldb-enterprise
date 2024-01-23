#!/bin/bash

source variables.sh


web_ingress_public_ip=$(jq -r '.nodes[] | select(has("web_ingress")) | .web_ingress.public_ip' config.json)

nomad_server_private_ip=$(jq -r '.nodes[] | select(has("nomad_server")) | .private_ip' config.json)

sql_server_database_password=$(jq -r '.nodes[] | select(has("sql_server")) | .sql_server.database_password' config.json)
shared_dir=$(jq -r '.nodes[] | select(has("shared_file_system")) | .shared_file_system.shared_dir' config.json)


# TODO: SSH into the nomad server node and launch/delete the jobs locally.

delete_model_bazaar_url="http://${web_ingress_public_ip}:4646/v1/job/modelbazaar"
delete_search_ui_url="http://${web_ingress_public_ip}:4646/v1/job/search-ui"

curl -s -X DELETE "$delete_model_bazaar_url"
curl -s -X DELETE "$delete_search_ui_url"

bash ../nomad/nomad_jobs/submit_nomad_job.sh $web_ingress_public_ip ../nomad/nomad_jobs/model_bazaar_job.hcl.j2 DB_PASSWORD=$sql_server_database_password SHARE_DIR=$shared_dir PUBLIC_SERVER_IP=$web_ingress_public_ip PRIVATE_SERVER_IP=$nomad_server_private_ip JWT_SECRET=$jwt_secret ADMIN_USERNAME=$admin_username ADMIN_MAIL=$admin_mail ADMIN_PASSWORD=$admin_password AUTOSCALING_ENABLED=$autoscaling_enabled AUTOSCALER_MAX_COUNT=$autoscaler_max_count GENAI_KEY=$genai_key
