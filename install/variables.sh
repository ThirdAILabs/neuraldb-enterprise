#!/bin/bash

# Should change these variables
license_path="/path/to/ndb_enterprise_license.json"  # license file must be named ndb_enterprise_license.json
jwt_secret="1234"  # this should be a password-like string 
admin_mail="admin@mail.com"
admin_username="admin"
admin_password="password"
genai_key="open-ai-api-key"

# S3 bucket support
aws_access_key="your-aws-iam-access-key"
aws_access_secret="your-aws-iam-acesss-secret"
aws_session_token="your-aws-iam-session-token"

# Application autoscaling parameters
autoscaling_enabled=false
autoscaler_max_count=1
