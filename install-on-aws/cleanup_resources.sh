#!/bin/bash

source variables.sh

instance_ids=$(aws ec2 describe-instances \
  --filters "Name=tag:Project,Values=${project_name}" \
  --query "Reservations[*].Instances[*].InstanceId" \
  --output text)

echo $instance_ids
aws ec2 terminate-instances --instance-ids $instance_ids
aws ec2 wait instance-terminated --instance-ids $instance_ids

subnet_ids=$(aws ec2 describe-subnets \
  --filters "Name=tag:Project,Values=${project_name}" \
  --query "Subnets[*].SubnetId" \
  --output text)

echo $subnet_ids
aws ec2 delete-subnet --subnet-id $subnet_ids


sg_ids=$(aws ec2 describe-security-groups \
  --filters "Name=tag:Project,Values=${project_name}" \
  --query "SecurityGroups[*].GroupId" \
  --output text)

echo $rt_ids
aws ec2 delete-security-group --group-id $sg_ids


rt_ids=$(aws ec2 describe-route-tables \
  --filters "Name=tag:Project,Values=${project_name}" \
  --query "RouteTables[*].RouteTableId" \
  --output text)

echo $rt_ids
aws ec2 delete-route-table --route-table-id $rt_ids


igw_ids=$(aws ec2 describe-internet-gateways \
  --filters "Name=tag:Project,Values=${project_name}" \
  --query "InternetGateways[*].InternetGatewayId" \
  --output text)

vpc_ids=$(aws ec2 describe-vpcs \
  --filters "Name=tag:Project,Values=${project_name}" \
  --query "Vpcs[*].VpcId" \
  --output text)

echo $igw_ids
aws ec2 detach-internet-gateway --internet-gateway-id $igw_ids --vpc-id $vpc_ids
aws ec2 delete-internet-gateway --internet-gateway-id $igw_ids

echo $vpc_ids
aws ec2 delete-vpc --vpc-id $vpc_ids