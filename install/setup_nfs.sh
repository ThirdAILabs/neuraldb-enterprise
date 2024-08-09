#!/bin/bash

node_ssh_username=$(jq -r '.ssh_username' config.json)

shared_dir=$(jq -r '.nodes[] | select(has("shared_file_system")) | .shared_file_system.shared_dir' config.json)

sudo yum -y check-update
sudo groupadd -g 4646 nomad_nfs || true
sudo useradd -u 4646 -g 4646 nomad_nfs || true
sudo usermod -a -G 4646 $node_ssh_username

sudo mkdir -p $shared_dir
sudo mkdir -p "$shared_dir/license"
sudo mkdir -p "$shared_dir/models"
sudo mkdir -p "$shared_dir/data"
sudo mkdir -p "$shared_dir/users"

sudo chown -R :4646 $shared_dir
sudo chmod -R 774 $shared_dir
sudo chmod -R g+s $shared_dir

sudo yum install -y nfs-utils
sudo yum install -y acl
sudo setfacl -d -R -m u::rwx,g::rwx,o::r $shared_dir