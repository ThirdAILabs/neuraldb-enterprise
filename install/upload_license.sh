#!/bin/bash

source variables.sh

shared_dir=$(jq -r '.nodes[] | select(has("shared_file_system")) | .shared_file_system.shared_dir' config.json)

sudo cp $license_path $shared_dir/license

if [ -n "$airgapped_license_path" ]; then
  sudo cp $airgapped_license_path $shared_dir/license
fi

sudo chmod g+rw $shared_dir/license/ndb_enterprise_license.json
