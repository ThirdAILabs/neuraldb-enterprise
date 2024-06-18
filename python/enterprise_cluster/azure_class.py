from azure.identity import AzureCliCredential
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.compute.models import VirtualMachineUpdate
from setup_cluster.ssh_client_handler import SSHClientHandler
import subprocess
import json


def get_subscription_id():
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
        self.logger.info(f"create_resource_group started")
        resource_group = self.resource_client.resource_groups.create_or_update(
            self.config["azure_resources"]["resource_group_name"],
            {"location": self.config["azure_resources"]["location"]},
        )
        self.logger.info(f"create_resource_group completed")
        self.created_resources.append(("resource_group", resource_group.name))
        return resource_group

    def create_vnet_and_subnet(self):
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
        """Deploys the entire infrastructure with one head node and multiple worker nodes."""
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
                    "nomad_server": False,
                }
            ],
            "ssh_username": self.config["vm_setup"]["ssh_username"],
        }

        # Fetch IP addresses from Azure and update config_data
        self.update_config_with_ips(config_data)

        return config_data

    def update_config_with_ips(self, config_data):
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
        config_data["nodes"][0].nomad_server = True

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

    def mount_disk(self, config_data):
        shared_file_system_private_ip = next(
            (
                node["private_ip"]
                for node in config_data["nodes"]
                if node["shared_file_system"]["create_nfs_server"]
            ),
            None,
        )
        web_ingress_data = next(
            (node for node in config_data["nodes"] if node["web_ingress"]["run_jobs"]),
            None,
        )
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
        # Reverse the resource creation order for deletion
        for resource_type, resource_name in reversed(self.created_resources):
            try:
                if resource_type == "vm":
                    self.logger.info(f"Deleting VM: {resource_name}")
                    self.compute_client.virtual_machines.begin_delete(
                        self.config["azure_resources"]["resource_group_name"],
                        resource_name,
                    ).wait()
                elif resource_type == "nic":
                    self.logger.info(f"Deleting NIC: {resource_name}")
                    self.network_client.network_interfaces.begin_delete(
                        self.config["azure_resources"]["resource_group_name"],
                        resource_name,
                    ).wait()
                elif resource_type == "public_ip":
                    self.logger.info(f"Deleting Public IP: {resource_name}")
                    self.network_client.public_ip_addresses.begin_delete(
                        self.config["azure_resources"]["resource_group_name"],
                        resource_name,
                    ).wait()
                elif resource_type == "subnet":
                    self.logger.info(f"Deleting Subnet: {resource_name}")
                    self.network_client.subnets.begin_delete(
                        self.config["azure_resources"]["resource_group_name"],
                        self.config["azure_resources"]["vnet_name"],
                        resource_name,
                    ).wait()
                elif resource_type == "vnet":
                    self.logger.info(f"Deleting VNet: {resource_name}")
                    self.network_client.virtual_networks.begin_delete(
                        self.config["azure_resources"]["resource_group_name"],
                        resource_name,
                    ).wait()
                elif resource_type == "resource_group":
                    self.logger.info(f"Deleting Resource Group: {resource_name}")
                    self.resource_client.resource_groups.begin_delete(
                        resource_name
                    ).wait()
                else:
                    self.logger.error(
                        f"Resource Type name not specified: {resource_type}"
                    )
            except Exception as e:
                self.logger.error(
                    f"Failed to delete {resource_type} {resource_name}: {e}. You may need to manually delete it."
                )
