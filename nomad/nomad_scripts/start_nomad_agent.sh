# Check for command-line argument
if [ "$#" -ne 4 ]; then
    echo "Usage: $0 <server_enabled> <client_enabled> <node_pool> <nomad_server_private_ip>"
    exit 1
fi

export $SERVER_ENABLED=$1
export $CLIENT_ENABLED=$2
export $NODE_POOL=$3
export $NOMAD_SERVER_PRIVATE_IP=$4

envsubst < ./nomad/nomad_node_configs/nomad_agent_config.hcl.tpl > ./nomad/nomad_node_configs/nomad_agent_config.hcl

sudo nomad agent -config=./nomad/nomad_node_configs/nomad_agent_config.hcl