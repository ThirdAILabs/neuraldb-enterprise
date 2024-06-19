import yaml
import argparse
import datetime
import time

from logger import LoggerConfig

from enterprise_cluster.aws_class import AWSInfrastructure
from enterprise_cluster.azure_class import AzureInfrastructure

from setup_cluster.create_nfs import NFSSetupManager
from setup_cluster.check_nfs import NodeStatusChecker
from setup_cluster.upload_license import UploadLicense
from setup_cluster.setup_nomad import NomadDeployer
from setup_cluster.setup_postgresql import SQLServerDeployer
from setup_cluster.launch_nomad_jobs import NomadJobDeployer
from setup_cluster.cluster_validate import ClusterValidator

from utils import validate_cluster_config


def load_yaml_config(filepath):
    try:
        with open(filepath, "r") as file:
            config = yaml.safe_load(file)
            return config
    except FileNotFoundError:
        print("The file was not found.")
    except yaml.YAMLError as exc:
        print("An error occurred during YAML parsing.", exc)


def merge_dictionaries(dict1, dict2):
    overlapping_keys = dict1.keys() & dict2.keys()
    if overlapping_keys:
        raise ValueError(f"Error: Overlapping keys found: {overlapping_keys}")

    merged_dict = {**dict1, **dict2}
    return merged_dict


def parse_arguments():
    parser = argparse.ArgumentParser(description="Load a YAML configuration file.")
    parser.add_argument(
        "-y",
        "--yaml",
        type=str,
        required=True,
        help="Path to the YAML configuration file",
    )
    parser.add_argument(
        "-l",
        "--logfile",
        type=str,
        required=False,
        default="neuraldb_enterprise.log",
        help="Path to the log file",
    )

    return parser.parse_args()


def main():
    args = parse_arguments()

    logger = LoggerConfig(log_file=args.logfile).get_logger(args.logfile)

    user_config = load_yaml_config(args.yaml)

    # Check yaml file content
    is_valid, msg = validate_cluster_config(user_config)
    if not is_valid:
        logger.error(f"Cluster Validation: {msg}")
        raise ValueError(msg)

    if user_config["cluster_type_config"] == "aws":
        instance_ids = vpc_id = subnet_id = sg_id = igw_id = rtb_id = None
        try:
            aws_infra = AWSInfrastructure(user_config, logger)

            key_pair_id = aws_infra.import_key_pair()
            vpc_id = aws_infra.create_vpc()
            subnet_id = aws_infra.create_subnet(vpc_id)
            igw_id = aws_infra.setup_internet_gateway(vpc_id)
            rtb_id = aws_infra.create_route_table(vpc_id, igw_id, subnet_id)
            sg_id = aws_infra.create_security_group(vpc_id)
            aws_infra.setup_security_group_rules(sg_id)
            instance_ids = aws_infra.launch_instances(sg_id, subnet_id)

            cluster_config = aws_infra.create_cluster_config(instance_ids)

        except Exception as e:
            logger.error(f"Error occurred: {e}. Initiating cleanup.")
            aws_infra.cleanup_resources(
                instance_ids=instance_ids,
                vpc_id=vpc_id,
                sg_id=sg_id,
                igw_id=igw_id,
                subnet_ids=[subnet_id],
                rtb_id=rtb_id,
                key_pair_name=user_config["ssh"]["key_name"],
            )
            raise

    elif user_config["cluster_type_config"] == "azure":
        try:
            azure_infra = AzureInfrastructure(user_config, logger)

            resource_group = azure_infra.create_resource_group()
            _, subnet = azure_infra.create_vnet_and_subnet()
            public_ip = azure_infra.create_public_ip()
            azure_infra.deploy_infrastructure(public_ip)
            azure_infra.create_and_configure_nsg()
            cluster_config = azure_infra.generate_config_json()
            azure_infra.mount_disk(cluster_config)
        except Exception as e:
            logger.error(f"An error occurred: {e}")
            azure_infra.cleanup_resources()
            raise

    elif user_config["cluster_type_config"] == "local":
        cluster_config = {}
        pass

    else:
        raise ValueError("Cluster Type Not Supported.")

    user_cluster_config = merge_dictionaries(user_config, cluster_config)

    validator = ClusterValidator(user_cluster_config, logger)
    result = validator.validate_cluster()
    logger.debug(f"Cluster validation: {result}")

    nfs_manager = NFSSetupManager(user_cluster_config, logger)
    try:
        nfs_manager.setup_shared_file_system()
        nfs_manager.setup_nfs_server()
        nfs_manager.mount_nfs_clients()
    except Exception as e:
        logger.error(f"Error occurred,  {e}")
        raise

    checker = NodeStatusChecker(user_cluster_config, logger)
    try:
        checker.check_status_on_nodes()
        checker.copy_status_file()
    except Exception as e:
        logger.error(f"Error occurred,  {e}")
        raise
    finally:
        checker.clean_up()

    cluster_setup = UploadLicense(user_cluster_config, logger)
    try:
        cluster_setup.transfer_files()
        cluster_setup.set_permissions()
    except Exception as e:
        logger.error(f"Error occurred,  {e}")
        raise

    deployer = NomadDeployer(user_cluster_config, logger)
    try:
        deployer.deploy()
        deployer.setup_nomad_cluster()
        deployer.bootstrap_acl_system()
        deployer.start_nomad_clients()
    except Exception as e:
        logger.error(f"Error occurred,  {e}")
        raise

    psql_deployer = SQLServerDeployer(user_cluster_config, logger)
    try:
        psql_deployer.deploy_sql_server()
    except Exception as e:
        logger.error(f"Error occurred,  {e}")
        raise

    nomad_job_deployer = NomadJobDeployer(user_cluster_config, logger)
    try:
        nomad_job_deployer.deploy_jobs()
    except Exception as e:
        logger.error(f"Error occurred,  {e}")
        raise

    # dumping the final cluster for info
    yaml_str = yaml.dump(user_cluster_config, default_flow_style=False, sort_keys=False)

    current_time = datetime.datetime.now()

    formatted_time = current_time.strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"neuraldb_cluster_config_{user_config['cluster_type_config']}_{formatted_time}.yaml"
    with open(filename, "w") as f:
        f.write(yaml_str)

    for node in user_cluster_config["nodes"]:
        if "web_ingress" in node and "public_ip" in node["web_ingress"]:
            public_ip = node["web_ingress"]["public_ip"]
            break

    # TODO(pratik): uvicorn takes time to start, figure out a way to clean that, and have more cleaner approach here.
    time.sleep(10)

    if public_ip:
        print(
            f"The Cluster Configuration has been saved. Use the public IP \033[91m{public_ip}\033[0m to access "
            f"the service. Simply copy the public IP into your browser's address bar."
        )
    else:
        raise ValueError("No public IP found in any node.")


if __name__ == "__main__":
    main()
