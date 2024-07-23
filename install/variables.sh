#!/bin/bash

# Should change these variables
license_path="/path/to/ndb_enterprise_license.json"  # license file must be named ndb_enterprise_license.json
jwt_secret="1234"  # this should be a password-like string

admin_mail="admin@mail.com"
admin_username="admin"
admin_password="password"

genai_key="open-ai-api-key"

# This variable determines which version of NeuralDB Enterprise to use.
# It is defaulted to 'latest', which will always pull the latest version of 
# NeuralDB Enterprise if the instance is started or restarted.
# To pin a version, you can specify a version number. Currently we have versions:
# "v0.1.0", "v0.1.1", "v0.1.2", and "v0.1.3". Dedicated version page coming soon.
ndb_enterprise_version="latest"


# Application autoscaling parameters
autoscaling_enabled=false
autoscaler_max_count=1
