#!/bin/bash

PUBLIC_NFS_SERVER_IP="$(jq -r '.HEADNODE_IP | .[0]' config.json)"
USERNAME=$admin_name

scp $license_path "$USERNAME"@$PUBLIC_NFS_SERVER_IP:$shared_dir/license

# Files moved from other directory or scp-ed file doesn't inherit required permission set by ACL.
ssh $USERNAME@$PUBLIC_NFS_SERVER_IP "sudo chmod g+w $shared_dir/license/ndb_enterprise_license.json"