# Check for command-line argument
if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <client|server> <nomad_server_private_ip>"
    exit 1
fi

case "$1" in
    client)
        sed -i "/^ *retry_join =/c\    retry_join = [\"$2:4647\"]" ./nomad/nomad_node_configs/client.hcl
        echo "$sudo_password" | sudo -S nomad agent -config=./nomad/nomad_node_configs/client.hcl
        ;;
    server)
        echo "$sudo_password" | sudo -S nomad agent -config=./nomad/nomad_node_configs/initial_server.hcl
        ;;
    *)
        echo "Invalid option. Use 'client' or 'server''"
        exit 1
        ;;
esac