#!/bin/bash

PUBLIC_IPS=()

json=$(<config.json)

nodes=("HEADNODE_IP" "CLIENTNODE_IP")
for node in "${nodes[@]}"; do
    ips=($(echo $json | jq -r ".${node}[]"))
    for ip in "${ips[@]}"; do
        PUBLIC_IPS+=("$ip")
    done
done


PRIVATE_IPS=()

json=$(<config.json)

nodes=("PRIVATE_HEADNODE_IP" "PRIVATE_CLIENTNODE_IP")
for node in "${nodes[@]}"; do
    ips=($(echo $json | jq -r ".${node}[]"))
    for ip in "${ips[@]}"; do
        PRIVATE_IPS+=("$ip")
    done
done

# Nomad Server IP
PUBLIC_SERVER_IP="${PUBLIC_IPS[0]}"
PRIVATE_SERVER_IP="${PRIVATE_IPS[0]}"

# Nomad Client IPs
PUBLIC_CLIENT_IPS=("${PUBLIC_IPS[@]:1}")
PRIVATE_CLIENT_IPS=("${PRIVATE_IPS[@]:1}")

SHARE_DIR="$(jq -r '.shared_dir' config.json)"
DB_PASSWORD=$db_password


bash ../nomad/nomad_jobs/submit_nomad_job.sh $PUBLIC_SERVER_IP ../nomad/nomad_jobs/search_ui_job.hcl.j2 PUBLIC_SERVER_IP=$PUBLIC_SERVER_IP
bash ../nomad/nomad_jobs/submit_nomad_job.sh $PUBLIC_SERVER_IP ../nomad/nomad_jobs/traefik_job.hcl.j2 PRIVATE_SERVER_IP=$PRIVATE_SERVER_IP
bash ../nomad/nomad_jobs/submit_nomad_job.sh $PUBLIC_SERVER_IP ../nomad/nomad_jobs/model_bazaar_job.hcl.j2 DB_PASSWORD=$DB_PASSWORD SHARE_DIR=$SHARE_DIR PUBLIC_SERVER_IP=$PUBLIC_SERVER_IP PRIVATE_SERVER_IP=$PRIVATE_SERVER_IP JWT_SECRET=$jwt_secret ADMIN_USERNAME=$admin_name ADMIN_MAIL=$admin_mail ADMIN_PASSWORD=$admin_password AUTOSCALING_ENABLED=$autoscaling_enabled AUTOSCALER_MAX_COUNT=$autoscaler_max_count GENAI_KEY=$genai_key
bash ../nomad/nomad_jobs/submit_nomad_job.sh $PUBLIC_SERVER_IP ../nomad/nomad_jobs/nomad_autoscaler_job.hcl