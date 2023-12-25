#!/bin/bash

PUBLIC_NFS_SERVER_IP="$(jq -r '.HEADNODE_IP | .[0]' config.json)"
USERNAME=$admin_name
NFS_SHARED_DIR="$(jq -r '.shared_dir' config.json)"

need_nfs=$(jq -r '.setup_nfs' config.json)

scp $license_path "$USERNAME"@$PUBLIC_NFS_SERVER_IP:$NFS_SHARED_DIR/license
