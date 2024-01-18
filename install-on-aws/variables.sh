#!/bin/bash

project_name="neuraldb-enterprise"

# Key pair for SSHing into instances
key_name="neuraldb-enterprise-key"
public_key_path="~/.ssh/id_rsa.pub"  # Change this to point to your machine's public key

# VPC/Subnet setup
region="us-east-1"
vpc_cidr_block="192.168.0.0/16"
subnet_cidr_block="192.168.0.0/24"

# Instances
instance_type="t2.xlarge"
vm_count=1  # vm_count must be greater than or equal to 0