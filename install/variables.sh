#!/bin/bash

# Should change these variables
license_path="/root/neuraldb-enterprise/ndb_enterprise_license.json"  # license file must be named ndb_enterprise_license.json
admin_name="root"
node_password="VMware1!"
db_password="password"
jwt_secret="CsnCr3lebs9eJQ"  # this should be a password-like string 
admin_mail="yash@thirdai.com"
admin_password="password"

# Application autoscaling parameters
autoscaling_enabled=false
autoscaler_max_count=1

# Shouldn't change these variables
nfs_shared_dir="/opt/neuraldb_enterprise/model_bazaar"
database_dir="/opt/neuraldb_enterprise/database"
