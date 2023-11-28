# Should change these variables
license_path="/Users/mjay/neuraldb-enterprise-services/model_bazaar/licensing/ndb_enterprise_license.json"  # license file must be named ndb_enterprise_license.json
resource_group_name="mjay-test-rg-5"
vnet_name="mjay-test-vnet-5"
subnet_name="mjay-test-subnet-5"
head_node_ipname="mjay-test-head-5"
admin_name="mjay"
db_password="password"
jwt_secret="uy7u983nis7dhduo23gyq"  # this should be a password-like string
admin_mail="mritunjay@thirdai.com"
admin_password="password"

# Can change these variables if desired
location="centralus"
vm_type="Standard_DS2_v2"
vm_count=5  # vm_count must be greater than or equal to 3

# Application autoscaling parameters
autoscaling_enabled=true
autoscaler_max_count=$((vm_count - 2)) # default, change according to your needs.

# Shouldn't change these variables
nfs_shared_dir="/model_bazaar"
postgresql_data_dir="/etc/postgresql/14/main"
