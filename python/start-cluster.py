import yaml
import argparse
from logger import LoggerConfig

from enterprise_cluster.aws_class import AWSInfrastructure
from enterprise_cluster.azure_class import AzureInfrastructure

from setup_cluster.create_nfs import NFSSetupManager
from setup_cluster.check_nfs import NodeStatusChecker
from setup_cluster.upload_license import UploadLicense
from setup_cluster.setup_nomad import NomadDeployer
from setup_cluster.setup_postgresql import SQLServerDeployer
from setup_cluster.launch_nomad_jobs import NomadJobDeployer
from setup_cluster.cluster_check import ClusterValidator


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
    # Check for overlapping keys
    overlapping_keys = dict1.keys() & dict2.keys()
    if overlapping_keys:
        raise ValueError(f"Error: Overlapping keys found: {overlapping_keys}")

    # If no overlaps, merge the two dictionaries
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
    return parser.parse_args()


def main():
    args = parse_arguments()

    logger = LoggerConfig(log_file="cluster.log").get_logger("cluster.log")
    logger.info(args)
    config = load_yaml_config(args.yaml)

    if config["cluster_type_config"] == "aws":
        instance_ids, vpc_id, subnet_id, sg_id, igw_id, rtb_id = (
            None,
            None,
            None,
            None,
            None,
            None,
        )
        try:
            aws_infra = AWSInfrastructure(config, logger)

            key_pair_id = aws_infra.import_key_pair()
            vpc_id = aws_infra.create_vpc()
            subnet_id = aws_infra.create_subnet(vpc_id)
            igw_id = aws_infra.setup_internet_gateway(vpc_id)
            rtb_id = aws_infra.create_route_table(vpc_id, igw_id, subnet_id)
            sg_id = aws_infra.create_security_group(vpc_id)
            aws_infra.setup_security_group_rules(sg_id)
            instance_ids = aws_infra.launch_instances(sg_id, subnet_id)
            nodes_config = aws_infra.create_cluster_config(instance_ids)
        except Exception as e:
            logger.error(f"Error occurred {e}, initiating cleanup.")
            aws_infra.cleanup_resources(
                instance_ids=instance_ids,
                vpc_id=vpc_id,
                sg_id=sg_id,
                igw_id=igw_id,
                subnet_ids=[subnet_id],
                rtb_id=rtb_id,
                key_pair_name=config["ssh"]["key_name"],
            )
    elif config["cluster_type_config"] == "azure":
        try:
            azure_vm_creator = AzureInfrastructure(config, logger)
            resource_group = azure_vm_creator.create_resource_group()
            logger.info(f"Resource Group created: {resource_group.id}")

            subnet = azure_vm_creator.create_vnet_and_subnet()
            logger.info(f"Subnet created: {subnet.id}")

            public_ip = azure_vm_creator.create_public_ip()
            logger.info(f"Public IP created: {public_ip.ip_address}")

            nic = azure_vm_creator.create_nic(public_ip)
            logger.info(f"NIC created: {nic.id}")

            for i in range(1, config["vm_setup"]["vm_count"] + 1):
                vm = azure_vm_creator.create_vm(nic.id, i)
                logger.info(f"VM {i} created: {vm.id}")

            nodes_config = azure_vm_creator.generate_config_json()
            logger.info(f"Configuration JSON generated successfully: {nodes_config}")

            azure_vm_creator.mount_disk(
                nodes_config,
            )

        except Exception as e:
            logger.error(f"An error occurred: {e}")

    # validate cluster
    # TODO(pratik): Write better names here.
    nodes_config = merge_dictionaries(config, nodes_config)

    validator = ClusterValidator(nodes_config)
    result = validator.validate_cluster()
    nfs_manager = NFSSetupManager(nodes_config, logger)
    try:
        nfs_manager.setup_shared_file_system()
        nfs_manager.setup_nfs_server()
        nfs_manager.mount_nfs_clients()
    except Exception as e:
        logger.error(f"Error occurred,  {e}")

    checker = NodeStatusChecker(nodes_config, logger)
    try:
        checker.check_status_on_nodes()
        checker.copy_status_file()
    except Exception as e:
        logger.error(f"Error occurred,  {e}")
    finally:
        checker.clean_up()

    cluster_setup = UploadLicense(nodes_config, logger)
    try:
        cluster_setup.transfer_files()
        cluster_setup.set_permissions()
    except Exception as e:
        logger.error(f"Error occurred,  {e}")

    deployer = NomadDeployer(nodes_config, logger)
    try:
        deployer.deploy()
        deployer.setup_nomad_cluster()
        deployer.bootstrap_acl_system()
        deployer.start_nomad_clients()
    except Exception as e:
        logger.error(f"Error occurred,  {e}")

    psql_deployer = SQLServerDeployer(nodes_config, logger)
    try:
        psql_deployer.deploy_sql_server()
    except Exception as e:
        logger.error(f"Error occurred,  {e}")

    nomad_job_deployer = NomadJobDeployer(nodes_config, logger)
    try:
        nomad_job_deployer.deploy_jobs()
    except Exception as e:
        logger.error(f"Error occurred,  {e}")


if __name__ == "__main__":
    main()
