# Define the image details

IMAGES=("model-bazaar"  "search-ui-job" "neuraldb-deploy" "neuraldb-train" "neuraldb-rlhf-update")
DOCKERNAME="NomadToken"
DOCKERPASSWORD="FO15fMI9CxZFn8fLL45ZiphDhNAA8SBGaHjfRCZHD0+ACRBr3VLA"
SERVER_ADDRESS="thirdaistaging.azurecr.io"

USERNAME=$admin_name

PUBLIC_SERVER_IP="$(jq -r '.HEADNODE_IP | .[0]' config.json)"

ssh -o StrictHostKeyChecking=no "$USERNAME"@$PUBLIC_SERVER_IP <<EOF
set -e

# Log in to the Docker registry
sudo docker login -u "$DOCKERNAME" -p "$DOCKERPASSWORD" "$SERVER_ADDRESS"

# Loop through the array and pull each Docker image
for IMAGE in ${IMAGES[@]}; do
  echo "Pulling image: thirdaistaging.azurecr.io/\$IMAGE:latest"
  sudo docker pull "thirdaistaging.azurecr.io/\$IMAGE:latest"

  echo "Tagging image: thirdaistaging.azurecr.io/\$IMAGE:latest -> $PRIVATE_NFS_SERVER_IP:5000/\$IMAGE"
  sudo docker tag "thirdaistaging.azurecr.io/\$IMAGE:latest" "$PRIVATE_NFS_SERVER_IP:5000/\$IMAGE"

  echo "Pushing image: $PRIVATE_NFS_SERVER_IP:5000/\$IMAGE"
  sudo docker push "$PRIVATE_NFS_SERVER_IP:5000/\$IMAGE"
done

# Log out from the Docker registry
sudo docker logout "$SERVER_ADDRESS" 
EOF