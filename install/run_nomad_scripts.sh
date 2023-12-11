#!/bin/bash

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <client|server>"
    exit 1
fi

declare -A config_map=( ["client"]="CLIENTNODE_IP" ["server"]="HEADNODE_IP" )

json=$(<config.json)

json_key=${config_map[$1]}
if [ -z "$json_key" ]; then
    echo "Invalid configuration: $1"
    exit 1
fi

ips=$(echo $json | jq -r ".${json_key}[]")
echo $ips

private_headnode_ip=$(jq -r '.PRIVATE_HEADNODE_IP[0]' config.json)
echo $private_headnode_ip

for ip in $ips; do
  conf=$1
  echo "Setting Up Nomad And Other Dependencies on the ip $ip"
  cat setup_nomad.sh | ssh -o StrictHostKeyChecking=no $admin_name@$ip "bash"

  echo "Running $conf on the ip $ip"
  ssh -o StrictHostKeyChecking=no $admin_name@$ip "\
    tmux has-session -t nomadServer 2>/dev/null && tmux kill-session -t nomadServer; \
    tmux new-session -d -s nomadServer 'cd neuraldb-enterprise; bash ./nomad/nomad_scripts/start_server.sh $conf $private_headnode_ip > head.log 2> head.err'"
done