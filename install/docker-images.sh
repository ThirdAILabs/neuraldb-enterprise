#!/bin/bash

# Define the image details
IMAGES=("model_bazaar"  "neuraldb_train_job" "neuraldb_update_job" "neuraldb_deployment_job" "neuraldb_frontend" "neuraldb_shard_allocation_job" "neuraldb_shard_train_job" "neuraldb_test_job")
DOCKERNAME="neuraldb-enterprise-pull"
DOCKERPASSWORD="yVGj3GVOJBJM4Lm+HOkvSfIZV435fHeHYVPgjyw2jt+ACRDwaC/l"
SERVER_ADDRESS="neuraldbenterprise.azurecr.io"

USERNAME=$admin_name

PUBLIC_IPS=()

json=$(<config.json)

nodes=("HEADNODE_IP" "CLIENTNODE_IP")
for node in "${nodes[@]}"; do
    ips=($(echo $json | jq -r ".${node}[]"))
    for ip in "${ips[@]}"; do
        PUBLIC_IPS+=("$ip")
    done
done

PUBLIC_SERVER_IP="${PUBLIC_IPS[0]}"
PUBLIC_CLIENT_IPS=("${PUBLIC_IPS[@]:1}")

PRIVATE_NFS_SERVER_IP="$(jq -r '.PRIVATE_HEADNODE_IP | .[0]' config.json)"

ssh -o StrictHostKeyChecking=no "$USERNAME"@$PUBLIC_SERVER_IP <<EOF
set -e

sudo docker run -d -p 5000:5000 --restart always --name registry registry:2

# Update Docker daemon configuration
DOCKER_DAEMON_CONFIG="/etc/docker/daemon.json"
sudo tee "\$DOCKER_DAEMON_CONFIG" > /dev/null <<EOL
{
    "insecure-registries" : ["$PRIVATE_NFS_SERVER_IP:5000"]
}
EOL

sudo systemctl restart docker                             

# Log in to the Docker registry
sudo docker login -u "$DOCKERNAME" -p "$DOCKERPASSWORD" "$SERVER_ADDRESS"

# Loop through the array and pull each Docker image
for IMAGE in ${IMAGES[@]}; do
  echo "Pulling image: neuraldbenterprise.azurecr.io/\$IMAGE:latest"
  sudo docker pull "neuraldbenterprise.azurecr.io/\$IMAGE:latest"

  echo "Tagging image: neuraldbenterprise.azurecr.io/\$IMAGE:latest -> $PRIVATE_NFS_SERVER_IP:5000/\$IMAGE"
  sudo docker tag "neuraldbenterprise.azurecr.io/\$IMAGE:latest" "$PRIVATE_NFS_SERVER_IP:5000/\$IMAGE"

  echo "Pushing image: $PRIVATE_NFS_SERVER_IP:5000/\$IMAGE"
  sudo docker push "$PRIVATE_NFS_SERVER_IP:5000/\$IMAGE"
done

# Log out from the Docker registry
sudo docker logout "$SERVER_ADDRESS" 
EOF

for ip in "${PUBLIC_CLIENT_IPS[@]}"; do
    ssh -o StrictHostKeyChecking=no "$USERNAME"@$ip <<EOF
    set -e

    # Update Docker daemon configuration
    DOCKER_DAEMON_CONFIG="/etc/docker/daemon.json"
    sudo tee "\$DOCKER_DAEMON_CONFIG" > /dev/null <<EOL
{
    "insecure-registries" : ["$PRIVATE_NFS_SERVER_IP:5000"]
}
EOL

sudo systemctl restart docker

EOF
done