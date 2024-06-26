from azure.identity import AzureCliCredential
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.compute.models import VirtualMachineUpdate
from setup_cluster.ssh_client_handler import SSHClientHandler
import subprocess
import json


def get_subscription_id():
    """
    Executes a command to retrieve the Azure subscription ID using the Azure CLI.

    Returns:
        str: The Azure subscription ID as a string.
    """
    
    result = subprocess.run(
        ["az", "account", "show", "--query", "id", "-o", "json"], stdout=subprocess.PIPE
    )
    subscription_id = json.loads(result.stdout.decode("utf-8").strip())
    return subscription_id


class AzureInfrastructure:
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger

        subscription_id = get_subscription_id()

        # TODO(pratik): Add info about filling up the azure credentials in documentation
        # https://learn.microsoft.com/en-us/dotnet/api/azure.identity.defaultazurecredential?view=azure-dotnet
        self.credential = AzureCliCredential()
        # https://learn.microsoft.com/en-us/python/api/azure-mgmt-resource/azure.mgmt.resource.resourcemanagementclient?view=azure-python
        self.resource_client = ResourceManagementClient(
            self.credential, subscription_id
        )
        # https://learn.microsoft.com/en-us/python/api/azure-mgmt-network/azure.mgmt.network.networkmanagementclient?view=azure-python
        self.network_client = NetworkManagementClient(self.credential, subscription_id)
        # https://learn.microsoft.com/en-us/python/api/azure-mgmt-compute/azure.mgmt.compute.computemanagementclient?view=azure-python
        self.compute_client = ComputeManagementClient(self.credential, subscription_id)
        self.created_resources = []

    def create_resource_group(self):
        """
        Creates or updates an Azure resource group based on configuration settings.

        This method handles the creation or updating of a resource group in Azure and 
        records the created resource group's name in the `created_resources` list.

        Returns:
            ResourceGroup: An instance of the created or updated Azure resource group.
        """
        
        self.logger.info(f"create_resource_group started")
        resource_group = self.resource_client.resource_groups.create_or_update(
            self.config["azure_resources"]["resource_group_name"],
            {"location": self.config["azure_resources"]["location"]},
        )
        self.logger.info(f"create_resource_group completed")
        self.created_resources.append(("resource_group", resource_group.name))
        return resource_group

    def create_vnet_and_subnet(self):
        """
        Creates a virtual network (VNet) and a subnet within an Azure resource group using configurations specified in the instance's configuration dictionary.
        It saves the created resources' names, and handles the Azure operations for creating the virtual network and subnet.

        Returns:
            tuple: A tuple containing the results of the VNet and subnet creation operations. Both elements are Azure operation poller objects, which can be resolved to get the final results of the asynchronous operations.

        """
        
        vnet_params = {
            "location": self.config["azure_resources"]["location"],
            "address_space": {"address_prefixes": ["10.0.0.0/16"]},
        }
        self.logger.info(
            f"Creating VNET: {self.config['azure_resources']['vnet_name']}"
        )
        vnet_result = self.network_client.virtual_networks.begin_create_or_update(
            self.config["azure_resources"]["resource_group_name"],
            self.config["azure_resources"]["vnet_name"],
            vnet_params,
        ).result()

        self.created_resources.append(
            ("vnet", self.config["azure_resources"]["vnet_name"])
        )

        subnet_params = {"address_prefix": "10.0.0.0/24"}
        self.logger.info(
            f"Creating Subnet: {self.config['azure_resources']['subnet_name']}"
        )
        subnet_result = self.network_client.subnets.begin_create_or_update(
            self.config["azure_resources"]["resource_group_name"],
            self.config["azure_resources"]["vnet_name"],
            self.config["azure_resources"]["subnet_name"],
            subnet_params,
        ).result()
        self.created_resources.append(
            ("subnet", self.config["azure_resources"]["subnet_name"])
        )
        return vnet_result, subnet_result

    def create_public_ip(self):
        """
        Creates a static public IP address in Azure under the specified resource group and with the specified name.
        
        The function retrieves the location, resource group name, and IP name from a configuration attribute of the class.
        It calls Azure's network client to create or update the public IP, and then adds the result to a list of created resources.

        Returns:
            public_ip (PublicIPAddress): The Azure PublicIPAddress object that was created or updated.
        """
        
        public_ip_params = {
            "location": self.config["azure_resources"]["location"],
            "public_ip_allocation_method": "Static",
        }
        self.logger.info(
            f"Creating Public IP: {self.config['azure_resources']['head_node_ipname']}"
        )
        public_ip = self.network_client.public_ip_addresses.begin_create_or_update(
            self.config["azure_resources"]["resource_group_name"],
            self.config["azure_resources"]["head_node_ipname"],
            public_ip_params,
        ).result()
        self.created_resources.append(("public_ip", public_ip))
        return public_ip

    def create_nic(self, vm_name, nic_name, public_ip_address=None):
        """
        Creates a network interface card (NIC) for a virtual machine in Azure.

        This function handles the creation of a NIC by configuring it either with a public IP
        address if provided, or with a dynamic private IP address otherwise. It uses the
        Azure SDK for Python to interact with the Azure network client

        Parameters:
            vm_name (str): The name of the virtual machine for which the NIC is being created.
                        This name is used to name the IP configuration.
            nic_name (str): The name of the network interface card to be created.
            public_ip_address (str, optional): The public IP address to associate with the NIC.
                                            If not provided, the NIC will be set up with a dynamic private IP.

        Returns:
            NetworkInterface: The created network interface card object.

        """
    
        subnet_info = self.network_client.subnets.get(
            self.config["azure_resources"]["resource_group_name"],
            self.config["azure_resources"]["vnet_name"],
            self.config["azure_resources"]["subnet_name"],
        )
        if public_ip_address:
            ip_conf = [
                {
                    "name": f"ipconfig{vm_name}",
                    "public_ip_address": public_ip_address,
                    "subnet": {"id": subnet_info.id},
                }
            ]
        else:
            ip_conf = [
                {
                    "name": f"ipconfig{vm_name}",
                    "subnet": {"id": subnet_info.id},
                    "private_ip_allocation_method": "Dynamic",
                }
            ]

        nic_params = {
            "location": self.config["azure_resources"]["location"],
            "ip_configurations": ip_conf,
        }
        self.logger.info(f"Creating NIC: {nic_name}")
        nic = self.network_client.network_interfaces.begin_create_or_update(
            self.config["azure_resources"]["resource_group_name"],
            nic_name,
            nic_params,
        ).result()
        self.created_resources.append(("nic", nic_name))
        return nic

    def create_vm(self, vm_name, nic):
        """
        Creates a virtual machine (VM) on Azure using specified parameters.

        This function reads the public SSH key, constructs the VM configuration with
        this key, sets up the OS and network profiles, and initiates the VM creation process.

        Parameters:
            vm_name (str): The name to assign to the virtual machine.
            nic (object): A network interface card (NIC) object that contains the network configuration
                        including its identifier.

        Returns:
            object: The result of the VM creation process, containing the VM's properties and status.

        """
        with open(self.config["ssh"]["public_key_path"], "rb") as key_file:
            public_key_material = key_file.read().decode("utf-8")
        vm_params = {
            "location": self.config["azure_resources"]["location"],
            "os_profile": {
                "computer_name": vm_name,
                "admin_username": self.config["vm_setup"]["ssh_username"],
                "linux_configuration": {
                    "disable_password_authentication": True,
                    "ssh": {
                        "public_keys": [
                            {
                                "path": f"/home/{self.config['vm_setup']['ssh_username']}/.ssh/authorized_keys",
                                "key_data": public_key_material,
                            }
                        ]
                    },
                },
            },
            "hardware_profile": {"vm_size": self.config["vm_setup"]["type"]},
            "storage_profile": {
                # https://learn.microsoft.com/en-us/azure/virtual-machines/linux/quick-create-template
                "image_reference": {
                    "publisher": "Canonical",
                    "offer": "0001-com-ubuntu-server-jammy",
                    "sku": "22_04-lts-gen2",
                    "version": "latest",
                }
            },
            "network_profile": {"network_interfaces": [{"id": nic.id}]},
        }
        self.logger.info(f"Creating VM={vm_name}...")
        vm_creation_result = (
            self.compute_client.virtual_machines.begin_create_or_update(
                self.config["azure_resources"]["resource_group_name"],
                vm_name,
                vm_params,
            ).result()
        )
        self.logger.info(f"VM-{vm_name} created successfully.")
        self.created_resources.append(("vm", vm_name))
        return vm_creation_result

    def attach_data_disk(self, vm_name):
        """
        Attaches a data disk to a specified virtual machine (VM) on Azure.

        This function handles the creation and attachment of a new data disk to an Azure VM.
        It first creates an empty premium data disk, then attaches it to the specified VM and 
        ensures that the data disk is associated with the VM's storage profile.

        Parameters:
        vm_name (str): The name of the VM to which the data disk will be attached. This VM must exist within
                    the resource group specified in the configuration.
        """
    
        disk_params = {
            "location": self.config["azure_resources"]["location"],
            "disk_size_gb": 1024,
            "creation_data": {"create_option": "Empty"},
            "sku": {"name": "Premium_LRS"},
        }
        self.logger.info("Creating data disk for Head VM...")
        disk_creation_result = self.compute_client.disks.begin_create_or_update(
            self.config["azure_resources"]["resource_group_name"],
            "DataDisk",
            disk_params,
        ).result()
        self.logger.info("Data disk created, attaching...")
        vm = self.compute_client.virtual_machines.get(
            self.config["azure_resources"]["resource_group_name"], vm_name
        )
        # Note(pratik): Each VM on Azure should have their unique lun
        # number. `0` is fine for now, given we have only one disk.
        data_disk = {
            "lun": 0,
            "name": "DataDisk",
            "create_option": "Attach",
            "managed_disk": {"id": disk_creation_result.id},
        }
        vm.storage_profile.data_disks.append(data_disk)
        async_vm_update = self.compute_client.virtual_machines.begin_update(
            self.config["azure_resources"]["resource_group_name"],
            vm_name,
            VirtualMachineUpdate(storage_profile=vm.storage_profile),
        )
        result = async_vm_update.result()
        self.logger.info(f"Data disk attached successfully: {result}")

    def deploy_infrastructure(self, public_ip_address):
        """
        Deploys the entire infrastructure with one head node and multiple worker nodes.
        This method orchestrates the deployment of an Azure cloud infrastructure
        consisting of one head virtual machine (VM) and multiple worker VMs. The head VM
        is assigned a public IP address. Worker VMs are created as specified in the configuration
        settings, but they are not assigned public IP addresses.

        Parameters:
            public_ip_address (str): The public IP address to assign to the head VM.

        The process includes:
        - Creating a network interface controller (NIC) for the head VM.
        - Creating the head VM using the NIC.
        - Attaching a data disk to the head VM.
        - Iteratively creating NICs and VMs for each worker based on configuration settings.
        
        """
        self.logger.info("Starting deployment of Azure infrastructure...")

        head_nic = self.create_nic(
            vm_name=f"Head", nic_name="NodeHeadNic", public_ip_address=public_ip_address
        )

        head_vm = self.create_vm("Head", head_nic)
        self.logger.info("Head VM created successfully.")

        self.attach_data_disk("Head")
        self.logger.info("Data disk attached to Head VM successfully.")

        for i in range(1, self.config["vm_setup"]["vm_count"]):
            # without public ip
            worker_nic = self.create_nic(vm_name=f"Node{i}", nic_name=f"Node{i}Nic")
            self.create_vm(f"Node{i}", worker_nic)
            self.logger.info(f"Worker VM Node{i} created.")

        self.logger.info("All VMs deployed successfully.")

    def create_and_configure_nsg(self):
        """
        Creates and configures a Network Security Group (NSG) with various security rules in Azure.

        Creates an NSG named 'allowall' in the specified resource group and location from the configuration.
        
        Configures NSG rules to allow all inbound and outbound traffic within the virtual network,
        allow SSH traffic from anywhere, and generic rules to allow all other inbound and outbound traffic.
        
        Updates network interfaces to include the newly created NSG.
        """


        self.logger.info(
            "Starting to create and configure network security group (NSG)"
        )
        resource_group_name = self.config["azure_resources"]["resource_group_name"]
        nsg_name = "allowall"

        # Create Network Security Group
        nsg_params = {"location": self.config["azure_resources"]["location"]}
        nsg_result = self.network_client.network_security_groups.begin_create_or_update(
            resource_group_name, nsg_name, nsg_params
        ).result()
        self.logger.info("Network security group created successfully.")

        # Create NSG rules
        # Allow all inbound and outbound traffic within the virtual network
        self.network_client.security_rules.begin_create_or_update(
            resource_group_name,
            nsg_name,
            "AllowAllInbound",
            {
                "priority": 100,
                "protocol": "*",
                "access": "Allow",
                "direction": "Inbound",
                "source_address_prefix": "VirtualNetwork",
                "destination_address_prefix": "VirtualNetwork",
                "source_port_range": "*",
                "destination_port_range": "*",
            },
        ).wait()
        self.network_client.security_rules.begin_create_or_update(
            resource_group_name,
            nsg_name,
            "AllowAllOutbound",
            {
                "priority": 100,
                "protocol": "*",
                "access": "Allow",
                "direction": "Outbound",
                "source_address_prefix": "VirtualNetwork",
                "destination_address_prefix": "VirtualNetwork",
                "source_port_range": "*",
                "destination_port_range": "*",
            },
        ).wait()

        # Allow SSH traffic from anywhere
        self.network_client.security_rules.begin_create_or_update(
            resource_group_name,
            nsg_name,
            "AllowSSH",
            {
                "priority": 110,
                "protocol": "Tcp",
                "access": "Allow",
                "direction": "Inbound",
                "source_address_prefix": "*",
                "destination_address_prefix": "*",
                "source_port_range": "*",
                "destination_port_range": "22",
            },
        ).wait()

        # Generic rule to allow all inbound traffic from anywhere
        self.network_client.security_rules.begin_create_or_update(
            resource_group_name,
            nsg_name,
            "AllowAllInboundGeneric",
            {
                "priority": 120,
                "protocol": "*",
                "access": "Allow",
                "direction": "Inbound",
                "source_address_prefix": "*",
                "destination_address_prefix": "*",
                "source_port_range": "*",
                "destination_port_range": "*",
            },
        ).wait()

        # Generic rule to allow all outbound traffic to anywhere
        self.network_client.security_rules.begin_create_or_update(
            resource_group_name,
            nsg_name,
            "AllowAllOutboundGeneric",
            {
                "priority": 130,
                "protocol": "*",
                "access": "Allow",
                "direction": "Outbound",
                "source_address_prefix": "*",
                "destination_address_prefix": "*",
                "source_port_range": "*",
                "destination_port_range": "*",
            },
        ).wait()

        self.logger.info("NSG rules configured successfully.")

        # Update network interfaces to include the NSG
        nic_names = ["NodeHeadNic"] + [
            f"Node{i}Nic" for i in range(1, self.config["vm_setup"]["vm_count"])
        ]
        for nic_name in nic_names:
            nic = self.network_client.network_interfaces.get(
                resource_group_name, nic_name
            )
            nic.network_security_group = {"id": nsg_result.id}
            self.network_client.network_interfaces.begin_create_or_update(
                resource_group_name, nic_name, nic
            ).wait()
        self.logger.info("Network interfaces updated with NSG successfully.")

        self.logger.info("NSG creation and configuration completed.")
 
    def generate_config_json(self):
        """
        This function constructs a JSON dictionary with default settings for various components
        such as web ingress, SQL server, and shared file systems within a cluster of nodes.
        It includes placeholders and default values, and updates these with actual IP addresses fetched from Azure

        Returns:
            dict: A dictionary containing structured configuration data with real IP addresses of the nodes
        """
    
        self.logger.info("Generating configuration JSON file.")

        # Define default config structure with placeholder values
        config_data = {
            "nodes": [
                {
                    "private_ip": "",
                    "web_ingress": {
                        "public_ip": "",
                        "run_jobs": True,
                        "ssh_username": self.config["vm_setup"]["ssh_username"],
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
            "ssh_username": self.config["vm_setup"]["ssh_username"],
        }

        # Fetch IP addresses from Azure and update config_data
        self.update_config_with_ips(config_data)

        return config_data

    def update_config_with_ips(self, config_data):
        """
        Updates the provided configuration dictionary with public and private IP addresses of the head node
        and private IP addresses of the client nodes.

        Parameters:
            config_data (dict): The configuration dictionary where IP addresses will be added. It must have a specific
                                structure with keys like 'nodes' and sub-keys appropriate for storing IP addresses.

        This function retrieves network interface card (NIC) information for the head node and client nodes within
        a specified Azure resource group. It fetches and updates the public IP address for the head node's web ingress
        and both public and private IP addresses for all configured VMs based on the setup defined in the `config`
        attribute of the class instance. The updated IPs are added to the 'config_data' dictionary provided.
        """
        
        # Fetch public and private IPs for the head node
        head_nic_name = "NodeHeadNic"

        # Retrieve NIC information for the head node
        nic = self.network_client.network_interfaces.get(
            self.config["azure_resources"]["resource_group_name"], head_nic_name
        )

        public_ip_id = nic.ip_configurations[0].public_ip_address.id
        public_ip_address = self.network_client.public_ip_addresses.get(
            resource_group_name=self.config["azure_resources"]["resource_group_name"],
            public_ip_address_name=public_ip_id.split("/")[-1],
        )

        config_data["nodes"][0]["web_ingress"][
            "public_ip"
        ] = public_ip_address.ip_address
        config_data["nodes"][0]["private_ip"] = nic.ip_configurations[
            0
        ].private_ip_address

        # Add client node IPs
        for i in range(1, self.config["vm_setup"]["vm_count"]):
            node_name = f"Node{i}"
            client_nic_name = f"{node_name}Nic"
            nic = self.network_client.network_interfaces.get(
                self.config["azure_resources"]["resource_group_name"],
                client_nic_name,
            )
            client_private_ip = nic.ip_configurations[0].private_ip_address
            config_data["nodes"].append({"private_ip": client_private_ip})

    def get_shared_file_system_private_ip(self, config_data):
        """
        Retrieves the private IP address of a node designated as a shared file system server.

        This function scans through a list of nodes within the provided configuration data. It looks
        for a node that is marked to create an NFS server.

        Parameters:
            config_data (dict): A dictionary containing the configuration data
            
        Returns:
            str or None: The private IP address of the node if found; otherwise, None.
        """
        shared_file_system_private_ip = None

        if "nodes" in config_data and isinstance(config_data["nodes"], list):
            for node in config_data["nodes"]:
                if "shared_file_system" in node and isinstance(
                    node["shared_file_system"], dict
                ):
                    if node["shared_file_system"].get("create_nfs_server") == True:
                        if "private_ip" in node and isinstance(node["private_ip"], str):
                            shared_file_system_private_ip = node["private_ip"]
                            break

        return shared_file_system_private_ip

    def get_node_with_web_ingress(self, config_data):
        """
        This function searches through a list of nodes within the given configuration data
        to find and return the first node that has a web ingress dictionary configured
        specifically to run jobs.

        Parameters:
            config_data (dict): A dictionary containing the configuration data

        Returns:
            dict: The first node containing a "web_ingress" dictionary with "run_jobs" set to True.
                Returns None if no such node is found.
        """
    
        node_with_web_ingress = None

        if "nodes" in config_data and isinstance(config_data["nodes"], list):
            for node in config_data["nodes"]:
                if "web_ingress" in node and isinstance(node["web_ingress"], dict):
                    if node["web_ingress"].get("run_jobs") == True:
                        node_with_web_ingress = node
                    break

        return node_with_web_ingress

    def mount_disk(self, config_data):
        """
        Mounts a disk on a remote machine within a specific configuration environment.

        This function retrieves IP addresses and SSH details from the configuration data,
        establishes an SSH connection using these details, and executes a series of shell
        commands to mount a disk on the specified remote machine. It also ensures that the
        disk mount persists across reboots by adding an entry to the fstab file.

        Parameters:
            config_data (dict): Configuration data containing necessary details such as
                IP addresses, SSH credentials, and other specific network and machine information.
        """
        
        shared_file_system_private_ip = self.get_shared_file_system_private_ip(
            config_data
        )
        web_ingress_data = self.get_node_with_web_ingress(config_data)
        web_ingress_private_ip = web_ingress_data["private_ip"]
        web_ingress_public_ip = web_ingress_data["web_ingress"]["public_ip"]
        web_ingress_ssh_username = web_ingress_data["web_ingress"]["ssh_username"]

        ssh_client_handler = SSHClientHandler(
            config_data["ssh_username"],
            web_ingress_ssh_username,
            web_ingress_public_ip,
            web_ingress_private_ip=web_ingress_private_ip,
            logger=self.logger,
        )

        use_jump = shared_file_system_private_ip != web_ingress_private_ip
        target_ip = (
            web_ingress_public_ip if not use_jump else shared_file_system_private_ip
        )
        # Commands to setup and mount the disk
        # Note(pratik): disk lun is 0, as we set it up already like that
        commands = f"""
            sudo apt -y update &&
            device_name="/dev/$(ls -l /dev/disk/azure/scsi1 | grep -oE "lun0 -> ../../../[a-z]+" | awk -F'/' '{{print $NF}}')" &&
            sudo mkfs.xfs $device_name &&
            sudo mkdir -p /opt/neuraldb_enterprise &&
            sudo mount $device_name /opt/neuraldb_enterprise &&
            fstab_entry="$device_name   /opt/neuraldb_enterprise   xfs   defaults   0   0" &&
            if ! grep -qF -- "$fstab_entry" /etc/fstab; then
                echo "$fstab_entry" | sudo tee -a /etc/fstab
            else
                echo 'fstab entry already exists'
            fi
        """

        # Execute the command on the remote machine
        output = ssh_client_handler.execute_commands([commands], target_ip, use_jump)
        if output:
            self.logger.info(f"Disk mounted successfully on {target_ip}")
        else:
            self.logger.error(f"Failed to mount disk on {target_ip}")

    def cleanup_resources(self):
        """
        Deletes the specified Azure resource group if it exists.

        This function retrieves the name of the resource group from the instance's
        configuration, checks if the resource group exists, and if it does, deletes it.

        """
        
        resource_group_name = self.config["azure_resources"]["resource_group_name"]

        try:
            self.logger.info(
                f"Checking if Resource Group {resource_group_name} exists..."
            )
            resource_group_exists = self.check_resource_group_exists(
                resource_group_name
            )

            if resource_group_exists:
                self.logger.info(f"Deleting Resource Group: {resource_group_name}")

                self.resource_client.resource_groups.begin_delete(
                    resource_group_name
                ).wait()

                self.logger.info(
                    f"Resource Group {resource_group_name} deleted successfully."
                )
            else:
                self.logger.info(
                    f"Resource Group {resource_group_name} does not exist. No deletion needed."
                )

        except Exception as e:
            self.logger.error(
                f"Failed to delete Resource Group {resource_group_name}: {e}. You may need to manually address this issue."
            )

    def check_resource_group_exists(self, resource_group_name):
        """Check if a specific Azure Resource Group exists"""
        try:
            resource_group = self.resource_client.resource_groups.get(
                resource_group_name
            )
            return True if resource_group else False
        except Exception as e:
            self.logger.info(f"Resource Group {resource_group_name} not found: {e}")
            return False
