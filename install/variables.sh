#!/bin/bash

# Should change these variables
license_path="path/to/ndb_enterprise_license.json"  # license file must be named ndb_enterprise_license.json
admin_name="admin"
db_password="password"
jwt_secret="1234"  # this should be a password-like string 
admin_mail="admin@mail.com"
admin_password="password"
genai_key="key-for-generative-ai"

# Application autoscaling parameters
autoscaling_enabled=false
autoscaler_max_count=1

# Shouldn't change these variables
database_dir="/opt/neuraldb_enterprise/database"

# change these variables if custom cluster need to be used
shared_dir=/home/admin/neuraldb_enterprise/model_bazaar
setup_nfs=true