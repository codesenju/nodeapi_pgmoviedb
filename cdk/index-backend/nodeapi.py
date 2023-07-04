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

class NodeApiStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Get  environment variable
        account = os.getenv("AWS_ACCOUNT_ID")
        ecs_cluster_name = os.getenv("ECS_CLUSTER_NAME")
        region = os.getenv("AWS_REGION")

        # Import existing VPC
        self.environment_name = 'VpcInfraStack'
        vpc = ec2.Vpc.from_lookup(
            self, "ImportedVpc",
            vpc_name='{}/ApiProjectVpc'.format(self.environment_name)
        )

       # Security Group Creation
        security_group = ec2.SecurityGroup.from_security_group_id(self, "ImportedSG", os.getenv("SG"))
        Elb_SG = ec2.SecurityGroup(self, "Elb_SG",vpc=vpc,security_group_name="Elb_SG",allow_all_outbound=False)
        Nodeapi_SG = ec2.SecurityGroup(self, "Nodeapi_SG",vpc=vpc,security_group_name="Nodeapi_SG",allow_all_outbound=False)
        Postgres_SG = ec2.SecurityGroup(self, "Postgres_SG",vpc=vpc,security_group_name="Postgres_SG",allow_all_outbound=False)
        Index_SG = ec2.SecurityGroup(self, "Index_SG",vpc=vpc,security_group_name="Index_SG",allow_all_outbound=False)
        Frontend_SG = ec2.SecurityGroup(self, "Frontend_SG",vpc=vpc,security_group_name="Frontend_SG",allow_all_outbound=False)
        efs_SG = ec2.SecurityGroup(self, "EFS_allowInbound2049_SG",vpc=vpc,security_group_name="PostgresEFS_SG",allow_all_outbound=False)

        # Add rules for ELB
        Elb_SG.add_ingress_rule(ec2.Peer.any_ipv4(),ec2.Port.tcp(80),description="Allow inbound 80 from from outside world")
        # Elb_SG.add_egress_rule(ec2.Peer.any_ipv4(),ec2.Port.tcp(5000),description="Allow outbound 5000 to targets") # Added automatically
        # Elb_SG.add_egress_rule(ec2.Peer.any_ipv4(),ec2.Port.tcp(3000),description="Allow outbound 3000 to targets") # Added automatically
        Elb_SG.add_egress_rule(ec2.Peer.any_ipv4(),ec2.Port.tcp_range(32768,60999),description="Allow outbound ECS ephemeral port range to targets") # https://docs.aws.amazon.com/AmazonECS/latest/APIReference/API_PortMapping.html
        #ELB_SG.add_egress_rule(ec2.Peer.any_ipv4(),ec2.Port.tcp(443),description="Allow outbound 443")

        # Add rules for Nodeapi
        Nodeapi_SG.add_ingress_rule(Index_SG,ec2.Port.tcp(3000),description="Allow inbound 3000 from index")
        Nodeapi_SG.add_egress_rule(Postgres_SG,ec2.Port.tcp(5432),description="Allow outbound 5432 to postgres")
        Nodeapi_SG.add_egress_rule(ec2.Peer.any_ipv4(),ec2.Port.tcp(443),description="Allow outbound 443")

        # Add rules for postgres
        Postgres_SG.add_ingress_rule(Nodeapi_SG,ec2.Port.tcp(5432),description="Allow inbound 5432 for postgres db from Nodeapi")
        Postgres_SG.add_egress_rule(efs_SG,ec2.Port.tcp(2049),description="Allow outbound 2049 for postgres db to EFS")
        Postgres_SG.add_egress_rule(ec2.Peer.any_ipv4(),ec2.Port.tcp(443),description="Allow outbound 443")

        # Add rules for Index
        Index_SG.add_ingress_rule(Frontend_SG ,ec2.Port.tcp(5000),description="Allow inbound 5000 from Frontend")
        Index_SG.add_egress_rule(Nodeapi_SG,ec2.Port.tcp(3000),description="Allow outbound 3000 to Nodeapi") 
        Index_SG.add_egress_rule(ec2.Peer.any_ipv4(),ec2.Port.tcp(5000),description="Allow outbound 5000 to index-backend")
        Index_SG.add_egress_rule(ec2.Peer.any_ipv4(),ec2.Port.tcp(443),description="Allow outbound 443")

        # Add rules for Frontend
        Frontend_SG.add_egress_rule(Index_SG,ec2.Port.tcp(5000),description="Allow outbound 5000 to index")
        Frontend_SG.add_egress_rule(ec2.Peer.any_ipv4(),ec2.Port.tcp(443),description="Allow outbound 443")
  
        # Create security group for postgres EFS Filesystem to allow inbound 2049
        efs_SG.add_ingress_rule(ec2.Peer.any_ipv4(),ec2.Port.tcp(2049),description="EFS Filesystem to allow inbound 2049 from anywhere")
        #postgresEFS_SG.add_egress_rule(ec2.Peer.any_ipv4(),ec2.Port.tcp(443),description="Allow outbound 443")

        # Import IAM task execution role
        existing_task_execution_role_name = "ecsTaskExecutionRole" 
        existing_task_execution_role_arn = f'arn:aws:iam::{account}:role/{existing_task_execution_role_name}'
        task_execution_role = iam.Role.from_role_arn(self, 'ImportedTaskExecutionRole', role_arn=existing_task_execution_role_arn)

        # Import IAM task role
        existing_task_role_name = "000A_ecsExecTaskRole"
        existing_task_role_arn = f'arn:aws:iam::{account}:role/{existing_task_role_name}'
        task_role = iam.Role.from_role_arn(self, 'ImportedEcsExecTaskRole', role_arn=existing_task_role_arn)

        ### Adding policies to Task Role ##
        #task_role.add_managed_policy(policy=iam.ManagedPolicy.from_aws_managed_policy_name("AWSAppMeshEnvoyAccess"))
        #task_role.add_managed_policy(policy=iam.ManagedPolicy.from_aws_managed_policy_name("AWSXRayDaemonWriteAccess"))
       
        ## Import Namespace api.local from EcsClusterStack ooutputs
        api_namespace= servicediscovery.PrivateDnsNamespace.from_private_dns_namespace_attributes(self, "ImportedNamespace",
            namespace_arn= cdk.Fn.import_value("ApiNamespaceArn"),
            namespace_id=cdk.Fn.import_value("ApiNamespaceId"),
            namespace_name=cdk.Fn.import_value("ApiNamespaceName"),
        )

        # Import ECS Cluster
        cluster = ecs.Cluster.from_cluster_attributes(self, "ImportedCluster",
            cluster_name=f"{ecs_cluster_name}",
            security_groups=[security_group],
            vpc=vpc,
            default_cloud_map_namespace=api_namespace
            
        )
       
        ######################
        ## INDEX BACKEND SERVICE ##### EC2 | BRIDGE | DYNAMIC PORT MAPPINGS OR FARGATE
        ######################

        ## Task Definition ##
        index_task_definition = ecs.TaskDefinition(self, "IndexTaskDef",
        execution_role=task_execution_role, 
        task_role=task_role,
        network_mode=ecs.NetworkMode.AWS_VPC,
        compatibility=ecs.Compatibility.EC2_AND_FARGATE,
        cpu="256",
        memory_mib="512",
        #runtime_platform=ecs.RuntimePlatform(
        #    operating_system_family=ecs.OperatingSystemFamily.LINUX,
        #    cpu_architecture=ecs.CpuArchitecture.ARM64
        #    ),
        #########################
        ## appmesh-proxy-start ##
        #proxy_configuration=ecs.AppMeshProxyConfiguration( 
        #    container_name="envoy", #App Mesh side card that will proxy the requests 
        #    properties=ecs.AppMeshProxyConfigurationProps(
        #        app_ports=[5000], # index application port
        #        proxy_ingress_port=15000, # side card default config
        #        proxy_egress_port=15001, # side card default config
        #        egress_ignored_i_ps=["169.254.170.2","169.254.169.254"], # side card default config
        #        ignored_uid=1337 # side card default config
        #    )
        #)
        ## appmesh-proxy-end ##
        #######################
        )

        ## Image ##
        # ECR
        # index_repo = ecr.Repository.from_repository_name(self,"IndexRepo",repository_name="index.api.local")
  

        ## Container ##
        index_container = index_task_definition.add_container(
           "index",
           # ECR
           #image=ecs.ContainerImage.from_ecr_repository(index_repo),
           image=ecs.ContainerImage.from_registry("codesenju/index.api.local:ecs"),
           logging=ecs.LogDrivers.aws_logs(stream_prefix="index"),
           memory_limit_mib=512,
           cpu=256,
           container_name="index",                 
       )
        
        ## Port Mapping ##
        index_container.add_port_mappings(ecs.PortMapping(container_port=5000,name="index"))

        
        ########################################################
        ## App Mesh envoy proxy container configuration START ##
        #index_envoy_container = index_task_definition.add_container(
        #    "CrystalServiceProxyContdef",
        #    #image=ecs.ContainerImage.from_registry("public.ecr.aws/appmesh/aws-appmesh-envoy:v1.18.3.0-prod"),
        #    image=ecs.ContainerImage.from_registry("public.ecr.aws/appmesh/aws-appmesh-envoy:arm64-v1.24.2.0-prod"),
        #    container_name="envoy",
        #    memory_reservation_mib=128,
        #    environment={
        #        "AWS_REGION": os.getenv('AWS_REGION'),
        #        "ENVOY_LOG_LEVEL": "debug",
        #        "ENABLE_ENVOY_STATS_TAGS": "1",
        #        # "ENABLE_ENVOY_XRAY_TRACING": "1",
        #        "APPMESH_RESOURCE_ARN": cdk.Fn.import_value("IndexVnArn")
        #    },
        #    essential=True,
        #    logging=ecs.LogDriver.aws_logs(
        #        stream_prefix='/index-mesh-envoy-container',
        #    ),
        #    health_check=ecs.HealthCheck(
        #        interval=cdk.Duration.seconds(5),
        #        timeout=cdk.Duration.seconds(10),
        #        retries=10,
        #        command=["CMD-SHELL","curl -s http://localhost:9901/server_info | grep state | grep -q LIVE"],
        #    ),
        #    user="1337"
        #)
        #
        #index_envoy_container.add_ulimits(ecs.Ulimit(
        #    hard_limit=15000,
        #    name=ecs.UlimitName.NOFILE,
        #    soft_limit=15000
        #    )
        #)

        ## Primary container needs to depend on envoy before it can be reached out
        #index_container.add_container_dependencies(ecs.ContainerDependency(
        #       container=index_envoy_container,
        #       condition=ecs.ContainerDependencyCondition.HEALTHY
        #   )
        #)
        ## App Mesh envoy proxy container configuration END ##
        ######################################################

        ## Service ##
        index_service = ecs.Ec2Service(self, "Index",
            cluster=cluster,
            task_definition=index_task_definition,
            enable_execute_command=True,
            capacity_provider_strategies=[ecs.CapacityProviderStrategy(
                capacity_provider="spot-api-capasity-provider", 
                weight=1,
            )],

            service_name="index",
            security_groups=[Index_SG],
            #service_connect_configuration=ecs.ServiceConnectProps(
            #    services=[ecs.ServiceConnectService(
            #        port_mapping_name="index",
            #        dns_name="index.api.local",
            #        discovery_name="index",
            #        port=5000
            #    )
            #    ],
            #    #log_driver=ecs.LogDriver.aws_logs(stream_prefix="index-envoy"),
            #)
        )
        #index_service.enable_service_connect(log_driver=ecs.LogDriver.aws_log(stream_prefix="index-envoy"))
        ## CloudMap ##
        index_service.enable_cloud_map(name="index")
        
        
        ###################################
        ## LOADBALANCING & ASUTO SCALING ##
        ###################################
    
        ## OUTPUT ###
        # Output the ARN of the ECS service to use in other Stacks.
        # - https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk/CfnOutput.html


app=cdk.App()
NodeApiStack(app, "NodeApiStack", env=cdk.Environment(account=os.getenv("AWS_ACCOUNT_ID"), region=os.getenv("AWS_REGION")),)
app.synth()