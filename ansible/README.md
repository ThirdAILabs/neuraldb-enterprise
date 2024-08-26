# ThirdAI Platform Deployment with Ansible

This project automates the deployment of ThirdAI Platform using Ansible. The playbook handles the setup and configuration of various components such as web ingress, SQL server, and NFS shared directories across multiple nodes.

## Prerequisites

- Ansible installed on the control machine.
- SSH access to all target nodes.
- A configuration file (`config.yml`) containing necessary variables and node definitions.

## Deployment

To deploy ThirdAI Platform, execute the following command:

```bash
cd ansible
ansible-playbook playbooks/test_deploy.yml --extra-vars "config_path=/path/to/your/config.yml"
