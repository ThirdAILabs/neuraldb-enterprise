#!/bin/bash

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <client|server>"
    exit 1
fi

declare -A config_map=( ["client"]="PRIVATE_CLIENTNODE_IP" ["server"]="HEADNODE_IP" )

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

NODEPASSD=$node_password
jump_user=$admin_name

if [ "$1" == "server" ]; then
  for ip in $ips; do
    conf=$1
    echo "Setting Up Nomad And Other Dependencies on the ip $ip"
    cat setup_nomad.sh | sshpass -p $NODEPASSD ssh -o StrictHostKeyChecking=no $jump_user@$ip "bash"

    echo "Running $conf on the ip $ip"
    sshpass -p $NODEPASSD ssh -o StrictHostKeyChecking=no $jump_user@$ip "\
      tmux has-session -t nomadServer 2>/dev/null && tmux kill-session -t nomadServer; \
      tmux new-session -d -s nomadServer 'cd neuraldb-enterprise; bash ./nomad/nomad_scripts/start_server.sh $conf $private_headnode_ip > head.log 2> head.err'"
  done
elif [ "$1" == "client" ]; then
  jump_node=$(jq -r '.HEADNODE_IP[0]' config.json)
  NFS_CLIENT=$(jq -r '.NFS_CLIENT_IP[0]' config.json)
  for ip in $ips; do
    conf=$1
    echo "Setting Up Nomad And Other Dependencies on the ip $ip"
    cat setup_nomad.sh | env SSHPASS="$NODEPASSD" sshpass -d 123 ssh -o ProxyCommand="sshpass -e ssh -W %h:%p $jump_user@$jump_node" $jump_user@$ip 123<<<$NODEPASSD "bash"

    echo "Running $conf on the ip $ip"
    env SSHPASS="$NODEPASSD" sshpass -d 123 ssh -o ProxyCommand="sshpass -e ssh -W %h:%p $jump_user@$jump_node" $jump_user@$ip 123<<<$NODEPASSD "\
      tmux has-session -t nomadClient 2>/dev/null && tmux kill-session -t nomadClient; \
      tmux new-session -d -s nomadClient 'cd neuraldb-enterprise; bash ./nomad/nomad_scripts/start_server.sh $conf $private_headnode_ip > client.log 2> client.err'"
  done
else
  echo "Invalid configuration: $1"
  exit 1
fi