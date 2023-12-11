#!/bin/bash

# Check if wget command exists
if ! command -v wget &> /dev/null; then
    echo "wget not found. Installing..."
    # Update package list
    sudo apt update
    # Install wget
    sudo apt install -y wget
else
    echo "wget is already installed."
fi


# Check if docker exists
if ! command -v docker &> /dev/null; then
    wget -O get-docker.sh https://get.docker.com/
    sh get-docker.sh
    docker run hello-world
else
    echo "Docker is already installed."
fi


keyring_file="/usr/share/keyrings/hashicorp-archive-keyring.gpg"
if [ -f "$keyring_file" ]; then
    # Remove the existing keyring file to avoid the prompt
    sudo rm "$keyring_file"
fi
wget -O- https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o "$keyring_file"
echo "deb [signed-by=$keyring_file] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
sudo apt-get update && sudo apt-get install -y nomad="1.6.2-1"