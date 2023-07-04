#!/usr/bin/env python3
# Reference:
# - https://ecsworkshop.com/app_mesh/appmesh-implementation/mesh-crystal-app/
# - https://docs.aws.amazon.com/cdk/api/v2/python/index.html

from aws_cdk import (
    Stack,
    aws_ecs as ecs,
    aws_ec2 as ec2,
    aws_autoscaling as autoscaling,
    aws_iam as iam,
    aws_appmesh as appmesh,
    aws_ecr as ecr,
    aws_ecr_assets as ecr_assets,
    aws_logs as logs,
    aws_servicediscovery as servicediscovery,
    aws_elasticloadbalancingv2 as elbv2,
    aws_ecs_patterns as ecs_patterns,
    aws_efs as efs
)
import os
from constructs import Construct
import aws_cdk as cdk
from aws_cdk.aws_ecr_assets import DockerImageAsset
import  cdk_ecr_deployment  as ecrdeploy

class SGStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Get  environment variable
        account = os.getenv("AWS_ACCOUNT_ID")
        ecs_cluster_name = os.getenv("ECS_CLUSTER_NAME")
        region = os.getenv("AWS_REGION")

        # Import existing VPC
        vpc = ec2.Vpc.from_lookup(
            self, "ImportedVpc",
            vpc_name='VpcInfraStack/ApiProjectVpc'
        )

       # Security Group Creation
        Elb_SG = ec2.SecurityGroup(self, "Elb_SG",vpc=vpc,security_group_name="Elb_SG",allow_all_outbound=False)
        Nodeapi_SG = ec2.SecurityGroup(self, "Nodeapi_SG",vpc=vpc,security_group_name="Nodeapi_SG",allow_all_outbound=False)
        Postgres_SG = ec2.SecurityGroup(self, "Postgres_SG",vpc=vpc,security_group_name="Postgres_SG",allow_all_outbound=False)
        Index_SG = ec2.SecurityGroup(self, "Index_SG",vpc=vpc,security_group_name="Index_SG",allow_all_outbound=False)
        Frontend_SG = ec2.SecurityGroup(self, "Frontend_SG",vpc=vpc,security_group_name="Frontend_SG",allow_all_outbound=False)
        Efs_SG = ec2.SecurityGroup(self, "EFS_allowInbound2049_SG",vpc=vpc,security_group_name="PostgresEFS_SG",allow_all_outbound=False)
        vgw_SG = ec2.SecurityGroup(self, "vgw_SG",vpc=vpc,security_group_name="vgw_SG",allow_all_outbound=False)
        
        # Add rules for ELB
        Elb_SG.add_ingress_rule(ec2.Peer.any_ipv4(),ec2.Port.tcp(80),description="Allow inbound HTTP from from outside world.")
        Elb_SG.add_ingress_rule(ec2.Peer.any_ipv4(),ec2.Port.tcp(443),description="Allow inbound HTTPS from from outside world.")
        Elb_SG.add_egress_rule(ec2.Peer.ipv4(vpc.vpc_cidr_block),ec2.Port.tcp_range(32768,60999),description="Allow outbound ECS ephemeral port range to targets.") # https://docs.aws.amazon.com/AmazonECS/latest/APIReference/API_PortMapping.html
        Elb_SG.add_egress_rule(Nodeapi_SG,ec2.Port.tcp(3000),description="Allow traffic to nodeaapi target on port 3000.")
        Elb_SG.add_egress_rule(Index_SG,ec2.Port.tcp(5000),description="Allow traffic to index target on port 5000.")
        Elb_SG.add_egress_rule(Frontend_SG,ec2.Port.tcp(5000),description="Allow traffic to frontend target on port 5000.")
        Elb_SG.add_egress_rule(vgw_SG,ec2.Port.tcp(5000),description="Allow traffic to Virtual Gateway target on port 5000.")
        Elb_SG.add_egress_rule(vgw_SG,ec2.Port.tcp(5000),description="Allow traffic to Virtual Gateway target on port 5000.")

        Elb_SG.add_egress_rule(ec2.Peer.ipv4(vpc.vpc_cidr_block),ec2.Port.tcp(5000),description="Allow outbound traffic on port 5000 to VPC CIDR block.") 
      
      
        # Add rules for Nodeapi
        Nodeapi_SG.add_ingress_rule(Index_SG,ec2.Port.tcp(3000),description="Allow inbound 3000 from index")
        Nodeapi_SG.add_ingress_rule(Elb_SG,ec2.Port.tcp(3000),description="Allow inbound 3000 from ELB")
        Nodeapi_SG.add_egress_rule(Postgres_SG,ec2.Port.tcp(5432),description="Allow outbound 5432 to postgres")
        Nodeapi_SG.add_egress_rule(ec2.Peer.any_ipv4(),ec2.Port.tcp(443),description="Allow outbound 443")

        # Add rules for postgres
        Postgres_SG.add_ingress_rule(Nodeapi_SG,ec2.Port.tcp(5432),description="Allow inbound 5432 for postgres db from Nodeapi")
        Postgres_SG.add_egress_rule(Efs_SG,ec2.Port.tcp(2049),description="Allow outbound 2049 for postgres db to EFS")
        Postgres_SG.add_egress_rule(ec2.Peer.any_ipv4(),ec2.Port.tcp(443),description="Allow outbound 443")

        # Add rules for Index
        Index_SG.add_ingress_rule(Frontend_SG ,ec2.Port.tcp(5000),description="Allow inbound 5000 from Frontend")
        Index_SG.add_egress_rule(Nodeapi_SG,ec2.Port.tcp(3000),description="Allow outbound 3000 to Nodeapi") 
        Index_SG.add_egress_rule(ec2.Peer.any_ipv4(),ec2.Port.tcp(5000),description="Allow outbound 5000 to index-backend")
        Index_SG.add_egress_rule(ec2.Peer.any_ipv4(),ec2.Port.tcp(443),description="Allow outbound 443")
        Index_SG.add_ingress_rule(Elb_SG,ec2.Port.tcp(5000),description="Allow inbound 5000 from ELB")

        # Add rules for Frontend
        Frontend_SG.add_egress_rule(Index_SG,ec2.Port.tcp(5000),description="Allow outbound 5000 to index")
        Frontend_SG.add_egress_rule(ec2.Peer.any_ipv4(),ec2.Port.tcp(443),description="Allow outbound 443")
        Frontend_SG.add_ingress_rule(Elb_SG,ec2.Port.tcp(5000),description="Allow inbound 5000 from ELB")

        # Add rules for Virtual Gateway
        vgw_SG.add_egress_rule(Frontend_SG,ec2.Port.tcp(5000),description="Allow outbound 5000 to Frontend")
        vgw_SG.add_egress_rule(ec2.Peer.any_ipv4(),ec2.Port.tcp(443),description="Allow outbound 443")
        vgw_SG.add_ingress_rule(Elb_SG,ec2.Port.tcp(5000),description="Allow inbound 5000 from ELB")
  
        # Create security group for postgres EFS Filesystem to allow inbound 2049
        Efs_SG.add_ingress_rule(ec2.Peer.any_ipv4(),ec2.Port.tcp(2049),description="EFS Filesystem to allow inbound 2049 from anywhere")
        #postgresEFS_SG.add_egress_rule(ec2.Peer.any_ipv4(),ec2.Port.tcp(443),description="Allow outbound 443")
  
        ## OUTPUT ###
        # Output the ARN of the ECS service to use in other Stacks.
        # - https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk/CfnOutput.html
        cdk.CfnOutput(self,"pgmoviedb_sg",value=Postgres_SG.security_group_id,export_name="pgmoviedbSGID")
        cdk.CfnOutput(self,"nodeapi_sg",value=Nodeapi_SG.security_group_id,export_name="nodeapiSGID")
        cdk.CfnOutput(self,"index_sg",value=Index_SG.security_group_id,export_name="indexSGID")
        cdk.CfnOutput(self,"frontend_sg",value=Frontend_SG.security_group_id,export_name="frontendSGID")
        cdk.CfnOutput(self,"elb_sg",value=Elb_SG.security_group_id,export_name="elbSGID")
        cdk.CfnOutput(self,"efs_sg",value=Efs_SG.security_group_id,export_name="efsSGID")
        cdk.CfnOutput(self,"vgw_sg",value=vgw_SG.security_group_id,export_name="vgwSGID")
       

app=cdk.App()
SGStack(app, "SGStack", env=cdk.Environment(account=os.getenv("AWS_ACCOUNT_ID"), region=os.getenv("AWS_REGION")),)
app.synth()