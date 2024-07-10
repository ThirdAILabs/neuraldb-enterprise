# Define the image details

IMAGES=("model_bazaar"  "neuraldb_train_job" "neuraldb_update_job" "neuraldb_deployment_job" "neuraldb_frontend" "neuraldb_shard_allocation_job" "neuraldb_shard_train_job" "neuraldb_test_job")
DOCKERNAME="neuraldb-enterprise-pull"
DOCKERPASSWORD="yVGj3GVOJBJM4Lm+HOkvSfIZV435fHeHYVPgjyw2jt+ACRDwaC/l"
SERVER_ADDRESS="neuraldbenterprise.azurecr.io"

USERNAME=$admin_name

PUBLIC_SERVER_IP="$(jq -r '.HEADNODE_IP | .[0]' config.json)"

ssh -o StrictHostKeyChecking=no "$USERNAME"@$PUBLIC_SERVER_IP <<EOF
set -e

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