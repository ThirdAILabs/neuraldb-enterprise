# Check for command-line argument
if [ "$#" -ne 6 ]; then
    echo "Usage: $0 <server_enabled> <client_enabled> <node_pool> <node_class> <nomad_server_private_ip> <node_private_ip> <node_public_ip>"
    exit 1
fi

export SERVER_ENABLED=$1
export CLIENT_ENABLED=$2
export NODE_POOL=$3

if [ "$4" != "default" ]; then
    export NODE_CLASS_STRING="node_class = \"${4}\""
else
    export NODE_CLASS_STRING=""
fi

export NOMAD_SERVER_PRIVATE_IP=$5
export NODE_PRIVATE_IP=$6


read -r -d '' private_host_network << EOF
  host_network "private" {
    cidr = "$6/32"
  }
EOF
export PRIVATE_HOST_NETWORK=$private_host_network


if [ "$7" != "" ]; then
    read -r -d '' public_host_network << EOF
  host_network "public" {
    cidr = "$7/32"
  }
EOF
    export PUBLIC_HOST_NETWORK=$public_host_network
else
    export PUBLIC_HOST_NETWORK=""
fi


envsubst < ./nomad/nomad_node_configs/nomad_agent_config.hcl.tpl > ./nomad/nomad_node_configs/nomad_agent_config.hcl

sudo nomad agent -config=./nomad/nomad_node_configs/nomad_agent_config.hcl
