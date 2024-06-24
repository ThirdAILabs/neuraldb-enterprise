import boto3
import time


class AWSInfrastructure:
    def __init__(self, config, logger):
        self.logger = logger
        self.config = config
        self.ec2 = boto3.client(
            "ec2",
            region_name=self.config["network"]["region"],
        )

    def import_key_pair(self):
        """
        Imports an SSH public key to an Amazon EC2 instance to enable SSH logins.
        This method assumes `self.config` contains necessary SSH details such as the public key path and key name.

        Returns:
            str: The unique identifier of the imported key pair if successful, or None if an error occurs.
        """
    
        try:
            with open(self.config["ssh"]["public_key_path"], "rb") as key_file:
                public_key_material = key_file.read()

            response = self.ec2.import_key_pair(
                KeyName=self.config["ssh"]["key_name"],
                PublicKeyMaterial=public_key_material,
            )
            self.logger.info(f"Key pair imported: {response}")
            return response["KeyPairId"]

        except Exception as e:
            self.logger.error(f"An unexpected error occurred: {str(e)}")
            return None

    def create_vpc(self):
        """
        Call the create_vpc method on the EC2 service client to create a new Virtual Private Cloud (VPC).
        
        The CIDR block for the new VPC is specified by `vpc_cidr_block` from the configuration.
        """
        
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
        """
        This method creates a subnet within a specified VPC in AWS using the EC2 service.
        
        Parameters:
            vpc_id: str - The ID of the VPC within which the subnet will be created.
        """
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
        """
        Creates a new internet gateway and tags it with the project name from the configuration.
        Attaches the newly created internet gateway to the VPC specified by the `vpc_id`.

        Parameters:
            vpc_id (str): The ID of the VPC to which the internet gateway will be attached.

        Returns:
            str: The ID of the newly created internet gateway.

        """
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
        """
        Creates a new route table in the specified VPC with a tag containing the project name.
        Creates a default route in the route table that directs all traffic (0.0.0.0/0) to the specified internet gateway.
        Associates the created route table with the specified subnet.

        Parameters:
            vpc_id (str): The ID of the VPC in which the route table is to be created.
            igw_id (str): The ID of the internet gateway to which the default route should be directed.
            subnet_id (str): The ID of the subnet to which the route table will be associated.

        Returns:
            str: The ID of the newly created route table.

        """
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
        """
        Creates a security group within the specified VPC with predefined rules and tags.
        The security group is configured to allow ingress for HTTP, HTTPS, SSH, and Nomad protocols.
        
        Parameters:
        vpc_id (str): The ID of the VPC where the security group will be created.

        Returns:
        str: The ID of the newly created security group.

        """
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
        """
        The function defines rules for incoming traffic to specific ports for TCP. 
        Authorizes these ingress rules to the specified security group.
        
        Parameters:
        sg_id (str): The security group ID to which the rules will be applied.

        """
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

    def check_ami_exists(self, name, description):
        """
        Check if an Amazon Machine Image (AMI) exists that match the given name and description.

        Parameters:
            name (str): The name of the AMI to search for.
            description (str): The description of the AMI to search for.

        Returns:
            str or None: The Image ID of the found AMI if one exists, otherwise None.
        """
    
        images = self.ec2.describe_images(
            Filters=[
                {"Name": "name", "Values": [name]},
                {"Name": "description", "Values": [description]},
            ]
        )
        for image in images.get("Images", []):
            self.logger.info(f"Found existing AMI: {image['ImageId']} with name {name}")
            return image["ImageId"]
        return None

    def wait_for_ami(self, ami_id, timeout=600):
        """
        Waits for an Amazon Machine Image (AMI) to become available within a specified timeout period.

        Parameters:
            ami_id (str): The unique identifier for the AMI to check.
            timeout (int, optional): The time in seconds to wait for the AMI to become available. Defaults to 600 seconds.

        Raises:
            TimeoutError: If the AMI does not become available within the specified timeout.
            Exception: Re-raises any exceptions that occur during the AMI state check.
        """
    
        start_time = time.time()
        while True:
            try:
                response = self.ec2.describe_images(ImageIds=[ami_id])
                state = response["Images"][0]["State"]
                self.logger.info(f"Current state of AMI {ami_id}: {state}")
                if state == "available":
                    self.logger.info(f"AMI {ami_id} is now available")
                    return
                time.sleep(10)
                if time.time() - start_time >= timeout:
                    raise TimeoutError(
                        f"AMI {ami_id} did not become available within {timeout} seconds"
                    )
            except Exception as e:
                self.logger.error(f"Error while checking AMI state: {str(e)}")
                raise

    def wait_for_instances(self, instance_ids, state="running", timeout=300):
        """
        Waits for specified EC2 instances to reach a desired state.

        This method uses AWS EC2 waiters to poll the state of instances at regular intervals until 
        they reach the specified state or until a timeout occurs.

        Parameters:
            instance_ids (list of str): A list of EC2 instance IDs that this method will wait on.
            state (str): The desired state of the instances to wait for. Defaults to "running".
            timeout (int): The maximum time in seconds to wait for the instances to reach the desired state. Defaults to 300 seconds.

        """
        
        waiter_name = f"instance_{state}"
        try:
            waiter = self.ec2.get_waiter(waiter_name)
        except ValueError as e:
            self.logger.error(f"Invalid waiter name: {waiter_name}")
            raise ValueError(f"Invalid waiter name: {waiter_name}") from e

        self.logger.info(
            f"Waiting for instances {instance_ids} to reach state '{state}'..."
        )

        try:
            waiter.wait(
                InstanceIds=instance_ids,
                WaiterConfig={"Delay": 15, "MaxAttempts": timeout // 15},
            )
            self.logger.info(f"Instances {instance_ids} are now in state '{state}'")

        except Exception as e:
            self.logger.error(f"Error while waiting for instances: {str(e)}")
            raise

    def launch_instances(self, sg_id, subnet_id):
        """
        Launches EC2 instances using a specified AMI and configuration settings.
        This method handles checking if a specified AMI exists or needs to be copied from a source region.
        After ensuring the AMI is available, it launches a specified number of EC2 instances according to the configuration,
        setting up each instance with appropriate network settings and tags.

        Parameters:
            sg_id (str): The security group ID to associate with the instances.
            subnet_id (str): The subnet ID where the instances will be launched.

        Returns:
            list: A list of instance IDs of the launched instances.

        """
        
        ami_id = "ami-0c7217cdde317cfec"  # Default AMI for us-east-1
        target_region = self.config["network"]["region"]
        ami_name = "ThirdAI-NeuralDB Copied AMI"
        description = "Copied AMI to " + target_region

        existing_ami_id = self.check_ami_exists(ami_name, description)
        if existing_ami_id:
            ami_id = existing_ami_id
            self.logger.info(f"Using existing AMI: {ami_id} in {target_region}")
        else:
            self.logger.info(f"No existing AMI found, copying AMI to {target_region}")
            response = self.ec2.copy_image(
                Name=ami_name,
                SourceImageId=ami_id,
                SourceRegion="us-east-1",
                Description=description,
            )
            ami_id = response["ImageId"]
            self.logger.info(f"AMI copied: {ami_id} to {target_region}")

            # Wait for the copied AMI to become available
            try:
                self.wait_for_ami(ami_id, timeout=300)  # Extend timeout to 5 minutes
            except TimeoutError as e:
                self.logger.error(str(e))
                raise

        instances = []
        for i in range(self.config["vm_setup"]["vm_count"]):  # Include head node
            network_interface = {
                "AssociatePublicIpAddress": True,
                "SubnetId": subnet_id,
                "DeviceIndex": 0,  # Primary network interface
                "Groups": [sg_id],
            }

            instance = self.ec2.run_instances(
                ImageId=ami_id,
                MinCount=1,
                MaxCount=1,
                InstanceType=self.config["vm_setup"]["type"],
                KeyName=self.config["ssh"]["key_name"],
                NetworkInterfaces=[network_interface],
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
            instances.append(instance["Instances"][0]["InstanceId"])
        self.logger.info(f"Instances Ids: {instances}")
        self.wait_for_instances(instances, state="running", timeout=300)
        return instances

    def create_cluster_config(self, instance_ids):
        """
        Create a configuration dictionary for a cluster based on a list of EC2 instance IDs.
        This function initializes a cluster configuration with predefined settings and updates
        it with the IP addresses of the given EC2 instances. The first instance is treated as the
        head node, and the remaining instances are treated as client nodes.

        Parameters:
            instance_ids (list): A list of EC2 instance IDs where the first ID is for the head node
                            and the rest are client nodes.

        Returns:
            dict: A dictionary containing the cluster configuration with nodes set up with
                web ingress settings, SQL server settings, shared file system settings,
                and the respective IP addresses for each node.
        """
    
        head_node_id = instance_ids[0]
        client_node_ids = instance_ids[1:]

        # Prepare the initial node configuration
        config_data = {
            "nodes": [
                {
                    "private_ip": "",
                    "web_ingress": {
                        "public_ip": "",
                        "run_jobs": True,
                        "ssh_username": "ubuntu",
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
            "ssh_username": "ubuntu",
        }

        # Fetch IP addresses for the head node
        head_node_info = self.ec2.describe_instances(InstanceIds=[head_node_id])
        head_instance = head_node_info["Reservations"][0]["Instances"][0]
        config_data["nodes"][0]["web_ingress"]["public_ip"] = head_instance.get(
            "PublicIpAddress", ""
        )
        config_data["nodes"][0]["private_ip"] = head_instance.get(
            "PrivateIpAddress", ""
        )

        # Update configuration with client nodes
        if client_node_ids:
            client_info = self.ec2.describe_instances(InstanceIds=client_node_ids)
            for reservation in client_info["Reservations"]:
                for instance in reservation["Instances"]:
                    new_node = {"private_ip": instance.get("PrivateIpAddress", "")}
                    config_data["nodes"].append(new_node)

        self.logger.info(f"Cluster Config: {config_data}")
        return config_data

    def cleanup_resources(self):
        """
        Cleans up all AWS resources associated with a specific project.
        This function retrieves all resource IDs associated with a project (like instances, subnets, security groups, etc.)
        and then proceeds to terminate and delete those resources.
        """
    
        project_name = self.config["project"]["name"]

        instance_ids = self.get_resource_ids("instance", project_name)
        subnet_ids = self.get_resource_ids("subnet", project_name)
        sg_ids = self.get_resource_ids("security-group", project_name)
        rt_ids = self.get_resource_ids("route-table", project_name)
        igw_ids = self.get_resource_ids("internet-gateway", project_name)
        vpc_ids = self.get_resource_ids("vpc", project_name)

        self.terminate_instances(instance_ids)
        self.delete_subnets(subnet_ids)
        self.delete_security_groups(sg_ids)
        self.delete_route_tables(rt_ids)
        self.detach_delete_internet_gateways(igw_ids)
        self.delete_vpcs(vpc_ids)

    def get_resource_ids(self, resource_type, project_name):
        """
        Retrieves the IDs of AWS resources filtered by project and type.

        Parameters:
            resource_type (str): The type of the AWS resource (e.g., 'instance', 'subnet').
            project_name (str): The name of the project to filter resources by.

        Returns:
            list: A list of resource IDs of the specified type and project.
        """
        
        if resource_type == "instance":
            reservations = self.ec2.describe_instances(
                Filters=[{"Name": "tag:Project", "Values": [project_name]}]
            )["Reservations"]
            return [
                inst["InstanceId"] for res in reservations for inst in res["Instances"]
            ]
        elif resource_type == "subnet":
            subnets = self.ec2.describe_subnets(
                Filters=[{"Name": "tag:Project", "Values": [project_name]}]
            )["Subnets"]
            return [subnet["SubnetId"] for subnet in subnets]
        elif resource_type == "security-group":
            sgs = self.ec2.describe_security_groups(
                Filters=[{"Name": "tag:Project", "Values": [project_name]}]
            )["SecurityGroups"]
            return [sg["GroupId"] for sg in sgs]
        elif resource_type == "route-table":
            rts = self.ec2.describe_route_tables(
                Filters=[{"Name": "tag:Project", "Values": [project_name]}]
            )["RouteTables"]
            return [rt["RouteTableId"] for rt in rts]
        elif resource_type == "internet-gateway":
            igws = self.ec2.describe_internet_gateways(
                Filters=[{"Name": "tag:Project", "Values": [project_name]}]
            )["InternetGateways"]
            return [igw["InternetGatewayId"] for igw in igws]
        elif resource_type == "vpc":
            vpcs = self.ec2.describe_vpcs(
                Filters=[{"Name": "tag:Project", "Values": [project_name]}]
            )["Vpcs"]
            return [vpc["VpcId"] for vpc in vpcs]
        return []

    def terminate_instances(self, instance_ids):
        """
        Terminate specified AWS EC2 instances and waits until termination is confirmed.

        Parameters:
            instance_ids (list): List of instance IDs to be terminated.
        """
    
        if instance_ids:
            self.ec2.terminate_instances(InstanceIds=instance_ids)
            self.ec2.get_waiter("instance_terminated").wait(InstanceIds=instance_ids)
            self.logger.info(f"Instances: {instance_ids} terminated.")

    def delete_subnets(self, subnet_ids):
        """
        Deletes a list of subnets
        """
        for subnet_id in subnet_ids:
            self.ec2.delete_subnet(SubnetId=subnet_id)
            self.logger.info(f"Subnet: {subnet_ids} deleted.")

    def delete_security_groups(self, sg_ids):
        """
        Deletes a list of security groups
        """
        for sg_id in sg_ids:
            self.ec2.delete_security_group(GroupId=sg_id)
            self.logger.info(f"Security group: {sg_ids} deleted.")

    def delete_route_tables(self, rt_ids):
        """
        Deletes a list of route tables
        """
        for rt_id in rt_ids:
            self.ec2.delete_route_table(RouteTableId=rt_id)
            self.logger.info(f"Route table: {rt_ids} deleted.")

    def detach_delete_internet_gateways(self, igw_ids):
        """
        Detaches and deletes a list of internet gateways 
        """
        for igw_id in igw_ids:
            self.ec2.detach_internet_gateway(InternetGatewayId=igw_id)
            self.ec2.delete_internet_gateway(InternetGatewayId=igw_id)
            self.logger.info(f"Internet gateway: {igw_ids} detached and deleted.")

    def delete_vpcs(self, vpc_ids):
        """
        Deletes a list of VPCs 
        """
        for vpc_id in vpc_ids:
            self.ec2.delete_vpc(VpcId=vpc_id)
            self.logger.info(f"VPC: {vpc_id} deleted.")
