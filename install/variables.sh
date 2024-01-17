#!/bin/bash

# Should change these variables
license_path="/Users/kartiksarangmath/Documents/thirdai/neuraldb-enterprise/install/ndb_enterprise_license.json"  # license file must be named ndb_enterprise_license.json
jwt_secret="1234"  # this should be a password-like string 
admin_mail="kartik@thirdai.com"
admin_username="kartik"
admin_password="password"
genai_key="key-for-generative-ai"

# Application autoscaling parameters
autoscaling_enabled=false
autoscaler_max_count=1