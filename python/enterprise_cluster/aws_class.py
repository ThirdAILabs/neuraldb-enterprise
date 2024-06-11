import boto3
import yaml
import logging


class AWSInfrastructure:
    def __init__(self, config, logger):
        self.logger = logger
        # TODO(pratik): Add a check whether all the required class is present or not
        self.config = config
        self.ec2 = boto3.client(
            "ec2",
            region_name=self.config["network"]["region"],
            public_key_material=config["ssh"]["public_key_path"],
        )

    def import_key_pair(self):
        with open(self.config["ssh"]["public_key_path"], "rb") as key_file:
            public_key_material = key_file.read()
        response = self.ec2.import_key_pair(
            KeyName=self.config["ssh"]["key_name"],
            PublicKeyMaterial=public_key_material,
        )
        self.logger.info(f"Key pair imported: {response}")
        return response["KeyPairId"]

    def create_vpc(self):
        response = self.ec2.create_vpc(
            CidrBlock=self.config["network"]["vpc_cidr_block"],
            TagSpecifications=[
                {
                    "ResourceType": "vpc",
                    "Tags": [
                        {"Key": "Project", "Value": self.config["project"]["name"]}
                    ],
                }
            ],
        )
        self.logger.info(f"VPC created: {response}")
        return response["Vpc"]["VpcId"]

    def create_subnet(self, vpc_id):
        response = self.ec2.create_subnet(
            VpcId=vpc_id,
            CidrBlock=self.config["network"]["subnet_cidr_block"],
            TagSpecifications=[
                {
                    "ResourceType": "subnet",
                    "Tags": [
                        {"Key": "Project", "Value": self.config["project"]["name"]}
                    ],
                }
            ],
        )
        self.logger.info(f"Subnet created: {response}")
        return response["Subnet"]["SubnetId"]

    def setup_internet_gateway(self, vpc_id):
        igw_response = self.ec2.create_internet_gateway(
            TagSpecifications=[
                {
                    "ResourceType": "internet-gateway",
                    "Tags": [
                        {"Key": "Project", "Value": self.config["project"]["name"]}
                    ],
                }
            ]
        )
        igw_id = igw_response["InternetGateway"]["InternetGatewayId"]
        self.ec2.attach_internet_gateway(VpcId=vpc_id, InternetGatewayId=igw_id)
        self.logger.info(f"Internet gateway setup: {igw_response}")
        return igw_id

    def create_route_table(self, vpc_id, igw_id, subnet_id):
        rt_response = self.ec2.create_route_table(
            VpcId=vpc_id,
            TagSpecifications=[
                {
                    "ResourceType": "route-table",
                    "Tags": [
                        {"Key": "Project", "Value": self.config["project"]["name"]}
                    ],
                }
            ],
        )
        rtb_id = rt_response["RouteTable"]["RouteTableId"]
        self.ec2.create_route(
            RouteTableId=rtb_id, DestinationCidrBlock="0.0.0.0/0", GatewayId=igw_id
        )
        self.ec2.associate_route_table(RouteTableId=rtb_id, SubnetId=subnet_id)
        self.logger.info(f"Route table created and configured: {rt_response}")
        return rtb_id

    def create_security_group(self, vpc_id):
        sg_response = self.ec2.create_security_group(
            GroupName="neuraldb-enterprise-node-sg",
            Description="allow ingress for http/s, ssh, and nomad",
            VpcId=vpc_id,
            TagSpecifications=[
                {
                    "ResourceType": "security-group",
                    "Tags": [
                        {"Key": "Project", "Value": self.config["project"]["name"]}
                    ],
                }
            ],
        )
        sg_id = sg_response["GroupId"]
        self.logger.info(f"Security group created: {sg_response}")
        return sg_id

    def setup_security_group_rules(self, sg_id):
        rules = [
            {
                "IpProtocol": "tcp",
                "FromPort": 22,
                "ToPort": 22,
                "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
            },
            {
                "IpProtocol": "tcp",
                "FromPort": 80,
                "ToPort": 80,
                "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
            },
            {
                "IpProtocol": "tcp",
                "FromPort": 443,
                "ToPort": 443,
                "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
            },
            {
                "IpProtocol": "tcp",
                "FromPort": 4646,
                "ToPort": 4646,
                "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
            },
            {
                "IpProtocol": "tcp",
                "FromPort": 5432,
                "ToPort": 5432,
                "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
            },
            {"IpProtocol": "all", "UserIdGroupPairs": [{"GroupId": sg_id}]},
        ]
        self.ec2.authorize_security_group_ingress(GroupId=sg_id, IpPermissions=rules)
        self.logger.info("Security group rules configured.")

    def launch_instances(self, sg_id, subnet_id):
        instances = self.ec2.run_instances(
            ImageId="ami-0c7217cdde317cfec",
            MinCount=1,
            MaxCount=self.config["vm_setup"]["vm_count"] + 1,  # Include head node
            InstanceType=self.config["vm_setup"]["type"],
            KeyName=self.config["ssh"]["key_name"],
            SecurityGroupIds=[sg_id],
            SubnetId=subnet_id,
            AssociatePublicIpAddress=True,
            BlockDeviceMappings=[
                {"DeviceName": "/dev/sda1", "Ebs": {"VolumeSize": 32}}
            ],
            TagSpecifications=[
                {
                    "ResourceType": "instance",
                    "Tags": [
                        {"Key": "Project", "Value": self.config["project"]["name"]}
                    ],
                }
            ],
        )
        self.logger.info(f"EC2 instances launched: {instances}")
        return [instance["InstanceId"] for instance in instances["Instances"]]

    def create_cluster_config(self, instances):
        instance_ids = [instance["InstanceId"] for instance in instances["Instances"]]
        head_node_id = instance_ids[0]
        client_node_ids = instance_ids[1:]

        # Update the configuration file with instance details
        config_data = {
            "nodes": [
                {
                    "private_ip": "",
                    "web_ingress": {
                        "public_ip": "",
                        "run_jobs": True,
                        "ssh_username": "admin",
                    },
                    "sql_server": {
                        "database_dir": "/opt/neuraldb_enterprise/database",
                        "database_password": "password",
                    },
                    "shared_file_system": {
                        "create_nfs_server": True,
                        "shared_dir": "/opt/neuraldb_enterprise/model_bazaar",
                    },
                    "nomad_server": True,
                }
            ],
            "ssh_username": "admin",
        }

        # Update IP addresses in config.json
        web_ingress_public_ip = self.ec2.describe_instances(InstanceIds=[head_node_id])[
            "Reservations"
        ][0]["Instances"][0]["PublicIpAddress"]
        web_ingress_private_ip = self.ec2.describe_instances(
            InstanceIds=[head_node_id]
        )["Reservations"][0]["Instances"][0]["PrivateIpAddress"]

        config_data["nodes"][0]["web_ingress"]["public_ip"] = web_ingress_public_ip
        config_data["nodes"][0]["private_ip"] = web_ingress_private_ip

        # Fetch and update client node private IPs in the config.json
        for client_node_id in client_node_ids:
            client_node_private_ip = self.ec2.describe_instances(
                InstanceIds=[client_node_id]
            )["Reservations"][0]["Instances"][0]["PrivateIpAddress"]
            new_node = {"private_ip": client_node_private_ip}
            config_data["nodes"].append(new_node)

        return config_data

    def cleanup_resources(
        self,
        instance_ids=None,
        vpc_id=None,
        sg_id=None,
        igw_id=None,
        subnet_ids=None,
        key_pair_name=None,
    ):
        try:
            if instance_ids:
                try:
                    self.ec2.terminate_instances(InstanceIds=instance_ids)
                    self.ec2.get_waiter("instance_terminated").wait(
                        InstanceIds=instance_ids
                    )
                except Exception as e:
                    self.logger.error(
                        f"Failed to detach or delete Internet Gateway {igw_id}: {str(e)}"
                    )

            # Detach and delete internet gateway if exists
            if igw_id and vpc_id:
                try:
                    self.ec2.detach_internet_gateway(
                        InternetGatewayId=igw_id, VpcId=vpc_id
                    )
                    self.ec2.delete_internet_gateway(InternetGatewayId=igw_id)
                    self.logger.info(f"Internet Gateway {igw_id} detached and deleted.")
                except Exception as e:
                    self.logger.error(
                        f"Failed to detach or delete Internet Gateway {igw_id}: {str(e)}"
                    )

            # Delete subnets if exist
            if subnet_ids:
                for subnet_id in subnet_ids:
                    try:
                        self.ec2.delete_subnet(SubnetId=subnet_id)
                        self.logger.info(f"Subnet {subnet_id} deleted.")
                    except Exception as e:
                        self.logger.error(
                            f"Failed to delete Subnet {subnet_id}: {str(e)}"
                        )

            # Delete security group if exists
            if sg_id:
                try:
                    self.ec2.delete_security_group(GroupId=sg_id)
                    self.logger.info(f"Security Group {sg_id} deleted.")
                except Exception as e:
                    self.logger.error(
                        f"Failed to delete Security Group {sg_id}: {str(e)}"
                    )

            # Delete VPC if exists
            if vpc_id:
                try:
                    self.ec2.delete_vpc(VpcId=vpc_id)
                    self.logger.info(f"VPC {vpc_id} deleted.")
                except Exception as e:
                    self.logger.error(f"Failed to delete VPC {vpc_id}: {str(e)}")

            # Delete key pair if exists
            if key_pair_name:
                try:
                    self.ec2.delete_key_pair(KeyName=key_pair_name)
                    self.logger.info(f"Key Pair {key_pair_name} deleted.")
                except Exception as e:
                    self.logger.error(
                        f"Failed to delete Key Pair {key_pair_name}: {str(e)}"
                    )

        except Exception as e:
            self.logger.error(f"General failure in cleanup_resources: {str(e)}")
