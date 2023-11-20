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
sengrid_key=""

# Can change these variables if desired
location="centralus"
vm_type="Standard_DS2_v2"
vm_count=3  # vm_count must be greater than or equal to 3

# Shouldn't change these variables
nfs_shared_dir="/model_bazaar"
postgresql_data_dir="/etc/postgresql/14/main"

