# Should change these variables
license_path="/Users/kartiksarangmath/Documents/thirdai/neuraldb-enterprise/install-on-azure/ndb_enterprise_license.json"  # license file must be named ndb_enterprise_license.json
resource_group_name="nomadkartik7"
vnet_name="nomadvnetkartik7"
subnet_name="nomadsubnetkartik7"
head_node_ipname="NomadHeadPublicIPkartik7"
admin_name="kartik"
db_password="password"
jwt_secret="HkGVfcyYQWLnbpAhUgZKPe"  # this should be a password-like string 
admin_mail="kartik@thirdai.com"
admin_password="password"

# Can change these variables if desired
location="centralus"
vm_type="Standard_DS2_v2"
vm_count=3  # vm_count must be greater than or equal to 3

# Application autoscaling parameters
autoscaling_enabled=false
autoscaler_max_count=$vm_count # default, change according to your needs.

# Shouldn't change these variables
nfs_shared_dir="/model_bazaar"
