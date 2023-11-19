# Check for command-line argument
if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <client|server|proxy_server> <nomad_server_private_ip>"
    exit 1
fi

case "$1" in
    client)
        sed -i "/^ *retry_join =/c\    retry_join = [\"$2:4647\"]" ./nomad/nomad_node_configs/client.hcl
        sudo nomad agent -config=./nomad_node_configs/client.hcl
        ;;
    server)
        sudo nomad agent -config=./nomad_node_configs/initial_server.hcl
        ;;
    proxy_server)
        sed -i "/^ *retry_join =/c\    retry_join = [\"$2:4647\"]" ./nomad/nomad_node_configs/proxy_client.hcl
        sudo nomad agent -config=./nomad_node_configs/proxy_client.hcl
        ;;
    *)
        echo "Invalid option. Use 'client', 'server', or 'proxy_server'"
        exit 1
        ;;
esac