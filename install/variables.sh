#!/bin/bash

# Should change these variables
license_path="/Users/gautamsharma/Desktop/ThirdAI/neuraldb-enterprise/azure/ndb_enterprise_license.json"  # license file must be named ndb_enterprise_license.json
admin_name="gautam"
db_password="password"
jwt_secret="CsnCr3lebs9eJQ"  # this should be a password-like string 
admin_mail="gautam@thirdai.com"
admin_password="password"
genai_key="key-for-generative-ai"

# Application autoscaling parameters
autoscaling_enabled=false
autoscaler_max_count=1

# Shouldn't change these variables
database_dir="/opt/neuraldb_enterprise/database"
