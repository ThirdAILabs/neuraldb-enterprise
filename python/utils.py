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
        "ndb_enterprise_version": {},
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
        "ndb_enterprise_version": {},
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
        "ndb_enterprise_version": {},
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


def check_sql_configuration(user_cluster_config, logger):
    sql_uri = None
    if "sql_configuration" in user_cluster_config:
        sql_config = user_cluster_config["sql_configuration"]

        # Check if use_external is true
        use_external = sql_config.get("use_external", False)
        if use_external:
            external_sql_uri = sql_config.get("external_sql_uri")
            if external_sql_uri:
                logger.info(
                    f"sql_configuration exists and use_external is True. Using specified database: {external_sql_uri}"
                )
                sql_uri = external_sql_uri
            else:
                logger.warning(
                    "sql_configuration exists and use_external is True, but no specified database. Initializing SQL database."
                )
        else:
            logger.info(
                "sql_configuration exists but use_external is False. Initializing SQL database."
            )
    else:
        logger.warning("sql_configuration does not exist. Initializing SQL database.")

    return sql_uri
