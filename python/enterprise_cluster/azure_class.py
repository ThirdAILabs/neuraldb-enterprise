from azure.identity import DefaultAzureCredential
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.compute import ComputeManagementClient
import logging
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

        # https://learn.microsoft.com/en-us/dotnet/api/azure.identity.defaultazurecredential?view=azure-dotnet
        self.credential = DefaultAzureCredential()
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
        try:
            resource_group = self.resource_client.resource_groups.create_or_update(
                self.config["azure_resources"]["resource_group_name"],
                {"location": self.config["azure_resources"]["location"]}
            )
            self.created_resources.append(("resource_group", resource_group.name))
            return resource_group
        except Exception as e:
            self.logger.error("Failed to create resource group: {0}".format(e))
            self.cleanup_resources()
            raise

    def create_vnet_and_subnet(self):
        try:
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

            subnet_params = {"address_prefix": "10.0.0.0/24"}
            self.logger.info(
                f"Creating Subnet: {self.config['azure_resources']['subnet_name']}"
            )
            subnet_result =  self.network_client.subnets.begin_create_or_update(
                self.config["azure_resources"]["resource_group_name"],
                self.config["azure_resources"]["vnet_name"],
                self.config["azure_resources"]["subnet_name"],
                subnet_params,
            ).result()
            
            self.created_resources.append(("vnet", self.config["azure_resources"]["vnet_name"]))
            self.created_resources.append(("subnet", rself.config["azure_resources"]["subnet_name"]))
            return subnet_result

         except Exception as e:
            self.logger.error("Failed to create vnet and subnet: {0}".format(e))
            self.cleanup_resources()
            raise

    def create_public_ip(self):
        try:
            public_ip_params = {
                "location": self.config["azure_resources"]["location"],
                "public_ip_allocation_method": "Static",
            }
            self.logger.info(
                f"Creating Public IP: {self.config['azure_resources']['head_node_ipname']}"
            )
            public_ip =  self.network_client.public_ip_addresses.begin_create_or_update(
                self.config["azure_resources"]["resource_group_name"],
                self.config["azure_resources"]["head_node_ipname"],
                public_ip_params,
            ).result()
            self.created_resources.append(("public_ip", public_ip))
            return public_ip

         except Exception as e:
            self.logger.error("Failed to create public_ips: {0}".format(e))
            self.cleanup_resources()
            raise
            

    def create_nic(self, public_ip_address):
        try:
            subnet_info = self.network_client.subnets.get(
                self.config["azure_resources"]["resource_group_name"],
                self.config["azure_resources"]["vnet_name"],
                self.config["azure_resources"]["subnet_name"],
            )
            nic_params = {
                "location": self.config["azure_resources"]["location"],
                "ip_configurations": [
                    {
                        "name": "ipconfig1",
                        "public_ip_address": public_ip_address,
                        "subnet": {"id": subnet_info.id},
                    }
                ],
            }
            self.logger.info(f"Creating NIC: NomadHeadNic")
            nic = self.network_client.network_interfaces.begin_create_or_update(
                self.config["azure_resources"]["resource_group_name"],
                "NomadHeadNic",
                nic_params,
            ).result()
            self.created_resources.append(("nic", "NomadHeadNic"))
            return nic

         except Exception as e:
            self.logger.error("Failed to create nic: {0}".format(e))
            self.cleanup_resources()
            raise

    def create_vm(self, nic_id, vm_id):
        try:
            vm_params = {
                "location": self.config["azure_resources"]["location"],
                "os_profile": {
                    "computer_name": "Head",
                    "admin_username": self.config["vm_setup"]["ssh_username"],
                    "admin_password": self.config["security"]["admin"]["password"],
                },
                "hardware_profile": {"vm_size": self.config["vm_setup"]["type"]},
                "storage_profile": {
                    "image_reference": {
                        "publisher": "Canonical",
                        "offer": "UbuntuServer",
                        "sku": "18.04-LTS",
                        "version": "latest",
                    }
                },
                "network_profile": {"network_interfaces": [{"id": nic_id}]},
            }
            self.logger.info(f"Creating VM: vm_{vm_id}")
            vms = self.compute_client.virtual_machines.begin_create_or_update(
                self.config["azure_resources"]["resource_group_name"], f"vm_{vm_id}", vm_params
            ).result()
            self.created_resources.append(("vm", f"vm_{vm_id}"))
            
         except Exception as e:
            self.logger.error("Failed to create vms: {0}".format(e))
            self.cleanup_resources()
            raise    

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
                        "nomad_server": True,
                    },
                    "sql_server": {
                        "database_dir": "/opt/neuraldb_enterprise/database",
                        "database_password": "password",
                    },
                    "shared_file_system": {
                        "create_nfs_server": True,
                        "shared_dir": "/opt/neuraldb_enterprise/model_bazaar",
                    },
                }
            ],
            "ssh_username": self.config["vm_setup"]["ssh_username"],
        }

        # Fetch IP addresses from Azure and update config_data
        self.update_config_with_ips(config_data)

        return config_data

    def update_config_with_ips(self, config_data):
        try:
            # Fetch public and private IPs for the head node
            head_node_name = "Head"
            head_nic_name = "NomadHeadNic"

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
            for i in range(1, self.config["vm_setup"]["vm_count"] + 1):
                node_name = f"Node{i}"
                client_nic_name = f"{node_name}VMNic"
                nic = self.network_client.network_interfaces.get(
                    self.config["azure_resources"]["resource_group_name"], client_nic_name
                )
                client_private_ip = nic.ip_configurations[0].private_ip_address
                config_data["nodes"].append({"private_ip": client_private_ip})
        except Exception as e:
            self.logger.error("Failed to create vms: {0}".format(e))
            self.cleanup_resources()
            raise  

    def mount_disk(
        self, config_data
    ):
        
        shared_file_system_private_ip = next((node["private_ip"] for node in config_data["nodes"] if node["shared_file_system"]["create_nfs_server"]), None)
        web_ingress_data = next((node for node in config_data["nodes"] if node["web_ingress"]["run_jobs"]), None)
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

        # Determine SSH command based on IP comparison
        if web_ingress_private_ip == shared_file_system_private_ip:
            ssh_command = f"ssh -o StrictHostKeyChecking=no {web_ingress_ssh_username}@{web_ingress_public_ip}"
        else:
            ssh_command = f"ssh -o StrictHostKeyChecking=no -J {web_ingress_ssh_username}@{web_ingress_public_ip} {config_data['ssh_username']}@{shared_file_system_private_ip}"

        # Determine if we use jump host based on IP comparison
        use_jump = shared_file_system_private_ip != web_ingress_private_ip
        target_ip = (
            web_ingress_private_ip if use_jump else shared_file_system_private_ip
        )

        # Get username for SSH
        ssh_username = self.config["vm_setup"]["ssh_username"]

        # Commands to setup and mount the disk
        commands = f"""
            sudo apt -y update &&
            disk_lun=$(az vm show --resource-group {resource_group_name} --name Head --query "storageProfile.dataDisks[?name=='DataDisk'].lun" -o tsv) &&
            device_name="/dev/$(ls -l /dev/disk/azure/scsi1 | grep -oE "lun$disk_lun -> ../../../[a-z]+" | awk -F'/' '{{print $NF}}')" &&
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
        output = ssh_client_handler.execute_commands(
            [commands], target_ip, use_jump
        )
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
                    self.compute_client.virtual_machines.begin_delete(self.config["azure_resources"]["resource_group_name"], resource_name).wait()
                elif resource_type == "nic":
                    self.logger.info(f"Deleting NIC: {resource_name}")
                    self.network_client.network_interfaces.begin_delete(self.config["azure_resources"]["resource_group_name"], resource_name).wait()
                elif resource_type == "public_ip":
                    self.logger.info(f"Deleting Public IP: {resource_name}")
                    self.network_client.public_ip_addresses.begin_delete(self.config["azure_resources"]["resource_group_name"], resource_name).wait()
                elif resource_type == "subnet":
                    self.logger.info(f"Deleting Subnet: {resource_name}")
                    self.network_client.subnets.begin_delete(self.config["azure_resources"]["resource_group_name"], self.config["azure_resources"]["vnet_name"], resource_name).wait()
                elif resource_type == "vnet":
                    self.logger.info(f"Deleting VNet: {resource_name}")
                    self.network_client.virtual_networks.begin_delete(self.config["azure_resources"]["resource_group_name"], resource_name).wait()
                elif resource_type == "resource_group":
                    self.logger.info(f"Deleting Resource Group: {resource_name}")
                    self.resource_client.resource_groups.begin_delete(resource_name).wait()
            except Exception as e:
                self.logger.error(f"Failed to delete {resource_type} {resource_name}: {e}")
