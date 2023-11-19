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


wget -O- https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
sudo apt update && sudo apt install nomad="1.6.2-1"