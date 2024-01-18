#!/bin/bash

source variables.sh

key_pair_id=$(aws ec2 import-key-pair --key-name $key_name --public-key-material "fileb://${public_key_path}" --query KeyPairId --output text)


# Create a Virtual Private Cloud 
vpc_id=$(aws ec2 create-vpc --region $region --cidr-block $vpc_cidr_block --tag-specifications "ResourceType=vpc,Tags=[{Key=Project,Value=${project_name}}]" --query Vpc.VpcId --output text)
echo "VPC ID: $vpc_id"

# Create Subnet 
subnet_id=$(aws ec2 create-subnet --vpc-id $vpc_id --cidr-block $subnet_cidr_block --tag-specifications "ResourceType=subnet,Tags=[{Key=Project,Value=${project_name}}]" --query Subnet.SubnetId --output text)
echo "Subnet ID: $subnet_id"

# Now setup internet-gateway and route-table associated with VPC
igw_id=$(aws ec2 create-internet-gateway --tag-specifications "ResourceType=internet-gateway,Tags=[{Key=Project,Value=${project_name}}]" --query InternetGateway.InternetGatewayId --output text)
aws ec2 attach-internet-gateway --vpc-id $vpc_id --internet-gateway-id $igw_id

rtb_id=$(aws ec2 create-route-table --vpc-id $vpc_id --tag-specifications "ResourceType=route-table,Tags=[{Key=Project,Value=${project_name}}]" --query RouteTable.RouteTableId --output text)
aws ec2 create-route --route-table-id $rtb_id --destination-cidr-block 0.0.0.0/0 --gateway-id $igw_id
aws ec2 associate-route-table --route-table-id $rtb_id --subnet-id $subnet_id

# Create security-group to control inbound/outbound traffic for EC2 instances
sg_id=$(aws ec2 create-security-group --group-name "neuraldb-enterprise-node-sg" --description "allow ingress for http/s, ssh, and nomad" --vpc-id $vpc_id --tag-specifications "ResourceType=security-group,Tags=[{Key=Project,Value=${project_name}}]"  --query 'GroupId' --output text)
echo "Security Group ID: $sg_id"

# Allow certain incoming traffic for instances in security group
aws ec2 authorize-security-group-ingress --group-id $sg_id --protocol tcp --port 22 --cidr 0.0.0.0/0
aws ec2 authorize-security-group-ingress --group-id $sg_id --protocol tcp --port 80 --cidr 0.0.0.0/0
aws ec2 authorize-security-group-ingress --group-id $sg_id --protocol tcp --port 443 --cidr 0.0.0.0/0
aws ec2 authorize-security-group-ingress --group-id $sg_id --protocol tcp --port 4646 --cidr 0.0.0.0/0
aws ec2 authorize-security-group-ingress --group-id $sg_id --protocol tcp --port 5432 --cidr 0.0.0.0/0
aws ec2 authorize-security-group-ingress --group-id $sg_id --protocol all --source-group $sg_id

# Now launch Head Node
head_node_id=$(aws ec2 run-instances --image-id ami-0c7217cdde317cfec \
  --count 1 \
  --instance-type $instance_type \
  --key-name $key_name \
  --security-group-ids $sg_id \
  --subnet-id $subnet_id \
  --associate-public-ip-address \
  --block-device-mappings 'DeviceName=/dev/sda1,Ebs={VolumeSize=32}' \
  --tag-specifications "ResourceType=instance,Tags=[{Key=Project,Value=${project_name}}]" \
  --query 'Instances[0].InstanceId' --output text)
echo "Head Node ID: $head_node_id"

client_node_ids=()
for ((i=0; i<$vm_count; i++))
do
  client_node_id=$(aws ec2 run-instances --image-id ami-0c7217cdde317cfec \
    --count 1 \
    --instance-type $instance_type \
    --key-name $key_name \
    --security-group-ids $sg_id \
    --subnet-id $subnet_id \
    --associate-public-ip-address \
    --block-device-mappings 'DeviceName=/dev/sda1,Ebs={VolumeSize=32}' \
    --tag-specifications "ResourceType=instance,Tags=[{Key=Project,Value=${project_name}}]" \
    --query 'Instances[0].InstanceId' --output text)
  echo "Client Node ID: $client_node_id"
  client_node_ids+=($client_node_id)
done


rm config.json
if [ ! -f "config.json" ]; then
  echo "{
  \"nodes\": [
    {
      \"private_ip\": \"\",
      \"web_ingress\": {
        \"public_ip\": \"\",
        \"run_jobs\": true,
        \"ssh_username\": \"ubuntu\"
      },
      \"sql_server\": {
        \"database_dir\": \"/opt/neuraldb_enterprise/database\",
        \"database_password\": \"password\"
      },
      \"shared_file_system\": {
        \"create_nfs_server\": true,
        \"shared_dir\": \"/opt/neuraldb_enterprise/model_bazaar\"
      },
      \"nomad_server\": true
    }
  ],
  \"ssh_username\": \"ubuntu\"
}" > config.json
fi


web_ingress_public_ip=$(aws ec2 describe-instances --instance-ids $head_node_id \
    --query 'Reservations[*].Instances[*].PublicIpAddress' \
    --output text)
jq --arg public_ip "$web_ingress_public_ip" '.nodes |= map(if has("web_ingress") then .web_ingress.public_ip = $public_ip else . end)' config.json > temp.json && mv temp.json config.json

web_ingress_private_ip=$(aws ec2 describe-instances --instance-ids $head_node_id \
    --query 'Reservations[*].Instances[*].PrivateIpAddress' \
    --output text)
jq --arg private_ip "$web_ingress_private_ip" '.nodes |= map(if .web_ingress then . + {"private_ip": $private_ip} else . end)' config.json > temp.json && mv temp.json config.json

for client_node_id in "${client_node_ids[@]}"
do
  client_node_private_ip=$(aws ec2 describe-instances --instance-ids $client_node_id \
    --query 'Reservations[*].Instances[*].PrivateIpAddress' \
    --output text)
  jq --arg private_ip "$client_node_private_ip" '.nodes += [{"private_ip": $private_ip}]' config.json > temp.json && mv temp.json config.json
done


