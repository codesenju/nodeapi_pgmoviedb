#!/usr/bin/env python3

# cdk v2
from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
)
import os
from constructs import Construct
import aws_cdk as cdk

class VpcInfraStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs,)

        # Create VPC and subnets
        vpc = ec2.Vpc(
            self, "ApiProjectVpc",
            ip_addresses=ec2.IpAddresses.cidr("17.0.0.0/16"),
            max_azs=3,
            vpc_name="ApiVpc",
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Public",
                    cidr_mask=24,
                    subnet_type=ec2.SubnetType.PUBLIC
                ),
                ec2.SubnetConfiguration(
                    name="Private",
                    cidr_mask=24,
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                )
            ]
        )

        # Create a security group that allows HTTP traffic on port 80
        security_group = ec2.SecurityGroup(self,"DefaultSecurityGroup",vpc=vpc,allow_all_outbound=False,description="Default security group")
        # security_group.add_ingress_rule(ec2.Peer.any_ipv4(),ec2.Port.tcp(80))

        ## Output ##
        cdk.CfnOutput(self,"ApiVpcId",value=vpc.vpc_id,export_name="ApiVpcId")
        # cdk.CfnOutput(self,"VpcArn",value=vpc.vpc_arn,export_name="VpcArn")
        cdk.CfnOutput(self,"ApiVpcDefaultSecurityGroupId",value=security_group.security_group_id,export_name="ApiVpcDefaultSecurityGroupId")


app = cdk.App()
# VPC Infra
VpcInfraStack(app, "VpcInfraStack", env=cdk.Environment(account=os.getenv('AWS_ACCOUNT_ID'), region=os.getenv('AWS_REGION')),)
# ECS Cluster
#EcsClusterStack(app, "EcsClusterStack", env=cdk.Environment(account=os.getenv('AWS_ACCOUNT_ID'), region=os.getenv('AWS_REGION')),)
app.synth()