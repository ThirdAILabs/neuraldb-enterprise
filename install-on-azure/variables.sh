# Should change these variables
license_path=""  # license file must be named ndb_enterprise_license.json
resource_group_name=""
vnet_name=""
subnet_name=""
head_node_ipname=""
admin_name=""
db_password=""
jwt_secret=""  # this should be a password-like string
admin_mail=""
admin_password=""

# Can change these variables if desired
location="centralus"
vm_type="Standard_B4ms"
vm_count=3  # vm_count must be greater than or equal to 0

# Application autoscaling parameters
autoscaling_enabled=false
autoscaler_max_count=$vm_count # default, change according to your needs.

# Shouldn't change these variables
nfs_shared_dir="/model_bazaar"
