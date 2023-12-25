#!/bin/bash

PUBLIC_NFS_SERVER_IP="$(jq -r '.HEADNODE_IP | .[0]' config.json)"
USERNAME=$admin_name
NFS_SHARED_DIR="$(jq -r '.shared_dir' config.json)"

need_nfs=$(jq -r '.setup_nfs' config.json)

scp $license_path "$USERNAME"@$PUBLIC_NFS_SERVER_IP:$NFS_SHARED_DIR/license

# if [ $need_nfs != true ]; then
    
# else
#     temp_license_location="/home/$USERNAME"
#     scp $license_path "$USERNAME"@$PUBLIC_NFS_SERVER_IP:$temp_license_location

#     ssh -o StrictHostKeyChecking=no "$USERNAME"@$PUBLIC_NFS_SERVER_IP << EOF
#     sudo mv $temp_license_location/ndb_enterprise_license.json $NFS_SHARED_DIR/license
#     sudo setfacl -m u::rwX,g::rwX,o::r-X $NFS_SHARED_DIR/license
# EOF
# fi
