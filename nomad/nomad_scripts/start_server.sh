# Check for command-line argument
if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <client|server> <nomad_server_private_ip> <node_private_ip>"
    exit 1
fi

case "$1" in
    client)
        sed -i "/^ *retry_join =/c\    retry_join = [\"$2:4647\"]" ./nomad/nomad_node_configs/client.hcl
        sed -i "/^ *http =/c\  http = \"$3\"" ./nomad/nomad_node_configs/client.hcl
        sed -i "/^ *rpc =/c\  rpc = \"$3\"" ./nomad/nomad_node_configs/client.hcl
        sed -i "/^ *serf =/c\  serf = \"$3\"" ./nomad/nomad_node_configs/client.hcl
        sudo nomad agent -config=./nomad/nomad_node_configs/client.hcl
        ;;
    server)
        sed -i "/^ *http =/c\  http = \"$3\"" ./nomad/nomad_node_configs/initial_server.hcl
        sed -i "/^ *rpc =/c\  rpc = \"$3\"" ./nomad/nomad_node_configs/initial_server.hcl
        sed -i "/^ *serf =/c\  serf = \"$3\"" ./nomad/nomad_node_configs/initial_server.hcl
        sudo nomad agent -config=./nomad/nomad_node_configs/initial_server.hcl
        ;;
    *)
        echo "Invalid option. Use 'client' or 'server''"
        exit 1
        ;;
esac