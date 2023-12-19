#!/bin/bash

echo "Installing Nomad"

repo_url="https://github.com/ThirdAILabs/neuraldb-enterprise.git"
repo_dir="neuraldb-enterprise"

# Check if the directory exists
if [ -d "$repo_dir" ]; then
    # If the directory exists, cd into it and pull the latest updates
    echo "Directory $repo_dir already exists. Pulling latest updates..."
    cd "$repo_dir" && git pull
else
    # If the directory does not exist, clone the repository
    echo "Cloning repository..."
    git clone "$repo_url" && cd "$repo_dir"
fi

sudo bash ./nomad/nomad_scripts/install_nomad.sh -y
