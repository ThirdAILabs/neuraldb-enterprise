# Should change these variables
license_path="path/to/ndb_enterprise_license.json"  # license file must be named ndb_enterprise_license.json
admin_name="admin"
db_password="password"
jwt_secret="1234"  # this should be a password-like string 
admin_mail="admin@mail.com"
admin_password="password"

# Application autoscaling parameters
autoscaling_enabled=false
autoscaler_max_count=$vm_count

# Shouldn't change these variables
nfs_shared_dir="/model_bazaar"
