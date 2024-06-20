def validate_keys(config, required_keys):
    for key, subkeys in required_keys.items():
        if key not in config:
            return False, f"Missing key: {key}"
        if subkeys:
            is_valid, message = validate_keys(config[key], subkeys)
            if not is_valid:
                return False, message
    return True, "All required keys are present"


def validate_cluster_config(config):
    local_required_keys = {
        "cluster_type_config": {},
        "project": {"name": {}},
        "nodes": [],
        "ssh_username": {},
        "security": {
            "license_path": {},
            "jwt_secret": {},
            "admin": {"email": {}, "username": {}, "password": {}},
        },
        "api": {"genai_key": {}},
        "autoscaling": {"enabled": {}, "max_count": {}},
    }
    aws_required_keys = {
        "cluster_type_config": {},
        "project": {"name": {}},
        "ssh": {"key_name": {}, "public_key_path": {}},
        "network": {"region": {}, "vpc_cidr_block": {}, "subnet_cidr_block": {}},
        "vm_setup": {"type": {}, "ssh_username": {}, "vm_count": {}},
        "security": {
            "license_path": {},
            "jwt_secret": {},
            "admin": {"email": {}, "username": {}, "password": {}},
        },
        "api": {"genai_key": {}},
        "autoscaling": {"enabled": {}, "max_count": {}},
    }
    azure_required_keys = {
        "cluster_type_config": {},
        "ssh": {"public_key_path": {}},
        "azure_resources": {
            "location": {},
            "resource_group_name": {},
            "vnet_name": {},
            "subnet_name": {},
            "head_node_ipname": {},
        },
        "vm_setup": {"type": {}, "ssh_username": {}, "vm_count": {}},
        "security": {
            "license_path": {},
            "jwt_secret": {},
            "admin": {"email": {}, "username": {}, "password": {}},
        },
        "api": {"genai_key": {}},
        "autoscaling": {"enabled": {}, "max_count": {}},
    }

    cluster_type = config.get("cluster_type_config")

    if cluster_type == "self-hosted":
        is_valid, message = validate_keys(config, local_required_keys)
    elif cluster_type == "aws":
        is_valid, message = validate_keys(config, aws_required_keys)
    elif cluster_type == "azure":
        is_valid, message = validate_keys(config, azure_required_keys)
    else:
        return False, "Unknown cluster type configuration"

    return is_valid, message
