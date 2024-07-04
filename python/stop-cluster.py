from logger import LoggerConfig

from utils import load_yaml_config, parse_arguments, validate_cluster_config

from enterprise_cluster.aws_class import AWSInfrastructure
from enterprise_cluster.azure_class import AzureInfrastructure

from setup_cluster.cleanup_cluster import CleanupSelfHostedCluster


def main():
    args = parse_arguments()

    logger = LoggerConfig(log_file=args.logfile).get_logger(args.logfile)

    user_config = load_yaml_config(args.yaml)

    is_valid, msg = validate_cluster_config(user_config)
    if not is_valid:
        logger.error(f"Cluster Validation: {msg}")
        raise ValueError(msg)

    if user_config["cluster_type_config"] == "aws":
        try:
            aws_infra = AWSInfrastructure(user_config, logger)
            aws_infra.cleanup_resources()
        except Exception as e:
            logger.error(f"An error occurred during cleanup: {e}.")
            raise

    elif user_config["cluster_type_config"] == "azure":
        try:
            azure_infra = AzureInfrastructure(user_config, logger)
            azure_infra.cleanup_resources()
        except Exception as e:
            logger.error(f"An error occurred during cleanup: {e}")
            raise

    elif user_config["cluster_type_config"] == "self-hosted":
        cleanup_self_hosted_cluster = CleanupSelfHostedCluster(user_config, logger)
        cleanup_self_hosted_cluster.cleanup_nomad_jobs()
        cleanup_self_hosted_cluster.cleanup_services()
        cleanup_self_hosted_cluster.cleanup_nomad_setup()
        cleanup_self_hosted_cluster.cleanup_nfs_setup()
        pass

    else:
        raise ValueError("Cluster Type Not Supported.")


if __name__ == "__main__":
    main()
