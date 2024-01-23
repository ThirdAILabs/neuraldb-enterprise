#!/bin/bash

source variables.sh

web_ingress_public_ip=$(jq -r '.nodes[] | select(has("web_ingress")) | .web_ingress.public_ip' config.json)
web_ingress_ssh_username=$(jq -r '.nodes[] | select(has("web_ingress")) | .web_ingress.ssh_username' config.json)

shared_dir=$(jq -r '.nodes[] | select(has("shared_file_system")) | .shared_file_system.shared_dir' config.json)

scp $license_path "$web_ingress_ssh_username"@$web_ingress_public_ip:$shared_dir/license

# Files moved from other directory or scp-ed file doesn't inherit required permission set by ACL.
ssh $web_ingress_ssh_username@$web_ingress_public_ip "sudo chmod g+rw $shared_dir/license/ndb_enterprise_license.json"