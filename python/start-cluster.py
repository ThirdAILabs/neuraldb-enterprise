import yaml
import argparse
from logger import LoggerConfig
from enterprise_cluster.aws_class import AWSInfrastructure
from setup_cluster.create_nfs import NFSSetupManager
from setup_cluster.check_nfs import NodeStatusChecker
from setup_cluster.upload_license import UploadLicense
from setup_cluster.setup_nomad import NomadDeployer
from setup_cluster.setup_postgresql import SQLServerDeployer
from setup_cluster.launch_nomad_jobs import NomadJobDeployer


def load_yaml_config(filepath):
    try:
        with open(filepath, "r") as file:
            config = yaml.safe_load(file)
            return config
    except FileNotFoundError:
        print("The file was not found.")
    except yaml.YAMLError as exc:
        print("An error occurred during YAML parsing.", exc)


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

    logger = LoggerConfig(log_file="cluster.log")
    logger.info(args)
    config = load_yaml_config(args.yaml)
    logger.info(config)

    if config["cluster_type_config"] == "aws":
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
            logger.error("Error occurred, initiating cleanup.")
            aws_infra.cleanup_resources(
                instance_ids=instance_ids,
                vpc_id=vpc_id,
                sg_id=sg_id,
                igw_id=igw_id,
                subnet_ids=[subnet_id],
                key_pair_name=config["ssh"]["key_name"],
            )

    nfs_manager = NFSSetupManager(config, logger)
    try:
        nfs_manager.setup_shared_file_system()
        nfs_manager.setup_nfs_server()
        nfs_manager.mount_nfs_clients()
    except Exception as e:
        logger.error(f"Error occurred,  {e}")

    checker = NodeStatusChecker(config, logger)
    try:
        checker.check_status_on_nodes()
        checker.copy_status_file()
    finally:
        checker.clean_up()

    cluster_setup = UploadLicense(config, logger)
    try:
        cluster_setup.transfer_files()
        cluster_setup.set_permissions()
    except Exception as e:
        logger.error(f"Error occurred,  {e}")

    deployer = NomadDeployer(config, logger)
    try:
        deployer.deploy()
        deployer.setup_nomad_cluster()
        deployer.bootstrap_acl_system()
        deployer.start_nomad_clients()
    except Exception as e:
        logger.error(f"Error occurred,  {e}")

    psql_deployer = SQLServerDeployer(config, logger)
    try:
        psql_deployer.deploy_sql_server()
    except Exception as e:
        logger.error(f"Error occurred,  {e}")

    nomad_job_deployer = NomadJobDeployer(config, logger)
    try:
        nomad_job_deployer.deploy_jobs()
    except Exception as e:
        logger.error(f"Error occurred,  {e}")


if __name__ == "__main__":
    main()
