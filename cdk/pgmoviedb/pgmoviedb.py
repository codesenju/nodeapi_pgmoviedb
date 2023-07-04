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

class PostgresStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Get  environment variable
        account = os.getenv("AWS_ACCOUNT_ID")
        ecs_cluster_name = "api"
        region = os.getenv("AWS_REGION")

        # Import existing VPC
        vpc = ec2.Vpc.from_lookup(
            self, "ImportedVpc",
            vpc_name='VpcInfraStack/ApiProjectVpc'
        )

        # Import Security groups
        security_group = ec2.SecurityGroup.from_security_group_id(self,"ImporteDefaultApiClusterSG",security_group_id=cdk.Fn.import_value("DefaultAPIClusterSG"))
        pgmoviedb_sg = ec2.SecurityGroup.from_security_group_id(self,"ImportedPgmoviedbSGID",security_group_id=cdk.Fn.import_value("pgmoviedbSGID"))
        efs_sg = ec2.SecurityGroup.from_security_group_id(self,"ImporteEfsSGID",security_group_id=cdk.Fn.import_value("efsSGID"))

        # Import IAM task execution role
        existing_task_execution_role_name = "ecsTaskExecutionRole" 
        existing_task_execution_role_arn = f'arn:aws:iam::{account}:role/{existing_task_execution_role_name}'
        task_execution_role = iam.Role.from_role_arn(self, 'ImportedTaskExecutionRole', role_arn=existing_task_execution_role_arn)

        # Import IAM task role
        existing_task_role_name = "000A_ecsExecTaskRole"
        existing_task_role_arn = f'arn:aws:iam::{account}:role/{existing_task_role_name}'
        task_role = iam.Role.from_role_arn(self, 'ImportedEcsExecTaskRole', role_arn=existing_task_role_arn)

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

        # Create the EFS file system
        efs_file_system = efs.FileSystem(self, "PG_EFSFileSystem",
        vpc=vpc,
        security_group=efs_sg,
        vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
        removal_policy=cdk.RemovalPolicy.DESTROY
        )
        ###################################
        ## Create the App Mesh resources ##
        ###################################
        # Import mesh
        mesh = appmesh.Mesh.from_mesh_arn(self,"ImportedEcsApiMesh",mesh_arn=cdk.Fn.import_value("EcsApiMeshArn"))
        ## Virtual Node ##
        pgmoviedb_node = appmesh.VirtualNode(self, "node",
            mesh=mesh,
            service_discovery=appmesh.ServiceDiscovery.dns("pgmoviedb.api.local"),
            listeners=[appmesh.VirtualNodeListener.tcp(
                port=5432,
                health_check=appmesh.HealthCheck.tcp(
                    healthy_threshold=3,
                    interval=cdk.Duration.seconds(5),
                    timeout=cdk.Duration.seconds(2),
                    unhealthy_threshold=2
                ),
                timeout=appmesh.TcpTimeout(
                    idle=cdk.Duration.seconds(5)
                )
            )],
            access_log=appmesh.AccessLog.from_file_path("/dev/stdout"),
            virtual_node_name="pgmoviedb-node"
        )
        ## Virtual Service ##
        pgmoviedb_virtual_service = appmesh.VirtualService(self, "pgmoviedbVirtualService",
            virtual_service_provider=appmesh.VirtualServiceProvider.virtual_node(pgmoviedb_node),
            virtual_service_name="pgmoviedb" + "." + api_namespace.namespace_name
        )

        ######################
        ## POSTGRES SERVICE ##   AWSVPC | FARGATE | EC2
        ######################

        ## Volume ##
        pg_volume = ecs.Volume(name="PGDATA",efs_volume_configuration={
                   "file_system_id": efs_file_system.file_system_id
        })

        ## EFS mount point ##
        pg_efs_mount_point = ecs.MountPoint(source_volume=pg_volume.name, 
                                        container_path="/var/lib/postgresql/data",
                                        read_only=False)

        ## Task Definition ##
        postgres_task_definition = ecs.TaskDefinition(self, "PostgresTaskDef",
        execution_role=task_execution_role,
        task_role=task_role,
        network_mode=ecs.NetworkMode.AWS_VPC,
        compatibility=ecs.Compatibility.EC2_AND_FARGATE,
        # Fargate runtime settings
        #runtime_platform=ecs.RuntimePlatform(
        #    operating_system_family=ecs.OperatingSystemFamily.LINUX,
        #    cpu_architecture=ecs.CpuArchitecture.ARM64
        #    ),
        volumes=[pg_volume],
        memory_mib="4096",
        cpu="2048",
        #########################
        ## appmesh-proxy-start ##
        proxy_configuration=ecs.AppMeshProxyConfiguration( 
            container_name="envoy", #App Mesh side card that will proxy the requests 
            properties=ecs.AppMeshProxyConfigurationProps(
                app_ports=[5432], # postgres application port
                proxy_ingress_port=15000, # side card default config
                proxy_egress_port=15001, # side card default config
                egress_ignored_ports=[2049], # EFS Mount
                egress_ignored_i_ps=["169.254.170.2","169.254.169.254"], # side card default config
                ignored_uid=1337 # side card default config
            )
        )
        ## appmesh-proxy-end ##
        #######################
        )
        # Create log group for container logs
        logGroup = logs.LogGroup(self,"PostgresLogGroup",
            log_group_name="/ecs/api/pgmoviedb",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=cdk.RemovalPolicy.DESTROY
        )
        ## Image ##
        # ECR
        # postgres_repo = ecr.Repository.from_repository_name(self,"PostgresRepo",repository_name="pgmoviedb.api.local")

        ## Container ##
        postgres_container = postgres_task_definition.add_container(
            "Postgres",
            image=ecs.ContainerImage.from_registry("codesenju/pgmoviedb.api.local:amd"),
            # ECR
            #image=ecs.ContainerImage.from_ecr_repository(postgres_repo),
            environment={
                "POSTGRES_DB": "movie",
                "POSTGRES_PASSWORD": "12345"
            },
            logging=ecs.LogDrivers.aws_logs(stream_prefix="postgres"),
            memory_reservation_mib=2048,
            #cpu=1024,
        )

        ## Mount Point ##
        postgres_container.add_mount_points(pg_efs_mount_point)
        
        ## Port Mappings
        postgres_container.add_port_mappings(ecs.PortMapping(container_port=5432,name="postgres",host_port=5432))
        
        ########################################################
        ## App Mesh envoy proxy container configuration START ##
        postgres_envoy_container = postgres_task_definition.add_container(
            "CrystalServiceProxyContdef",
            image=ecs.ContainerImage.from_registry("public.ecr.aws/appmesh/aws-appmesh-envoy:v1.25.1.0-prod"),
            #image=ecs.ContainerImage.from_registry("public.ecr.aws/appmesh/aws-appmesh-envoy:arm64-v1.24.2.0-prod"),
            container_name="envoy",
            memory_reservation_mib=128,
            #cpu=256,
            environment={
                "AWS_REGION": os.getenv('AWS_REGION'),
                "ENVOY_LOG_LEVEL": "debug",
                "ENABLE_ENVOY_STATS_TAGS": "1",
                "ENABLE_ENVOY_XRAY_TRACING": "1",
                "APPMESH_RESOURCE_ARN": pgmoviedb_node.virtual_node_arn
            },
            essential=True,
            logging=ecs.LogDriver.aws_logs(
                stream_prefix='/envoy-container',
                log_group=logGroup
            ),
            health_check=ecs.HealthCheck(
                interval=cdk.Duration.seconds(5),
                timeout=cdk.Duration.seconds(10),
                retries=10,
                command=["CMD-SHELL","curl -s http://localhost:9901/server_info | grep state | grep -q LIVE"],
            ),
            user="1337"
        )
        
        postgres_envoy_container.add_ulimits(ecs.Ulimit(
            hard_limit=15000,
            name=ecs.UlimitName.NOFILE,
            soft_limit=15000
            )
        )

        ## Primary container needs to depend on envoy before it can be reached out
        postgres_container.add_container_dependencies(ecs.ContainerDependency(
               container=postgres_envoy_container,
               condition=ecs.ContainerDependencyCondition.HEALTHY
           )
        )
        ## App Mesh envoy proxy container configuration END ##
        ######################################################

        ## Enable app mesh Xray observability ##
        #ammmesh-xray-uncomment
        xray_container = postgres_task_definition.add_container(
             "NodeapiXrayContainer",
             image=ecs.ContainerImage.from_registry("amazon/aws-xray-daemon"),
             logging=ecs.LogDriver.aws_logs(
                 stream_prefix='/xray-container',
                 log_group=logGroup
             ),
             essential=True,
             container_name="xray",
             memory_reservation_mib=512,
             #cpu=256,
             user="1337",
             environment={
                "AWS_REGION": region,
            },
         )
    
        postgres_envoy_container.add_container_dependencies(ecs.ContainerDependency(
               container=xray_container,
               condition=ecs.ContainerDependencyCondition.START
           )
         )
        #ammmesh-xray-uncomment
        
        ## Otel Container - START ##
        postgres_otel_container = postgres_task_definition.add_container(
             "NodeapiOtelContainer",
             image=ecs.ContainerImage.from_registry("codesenju/aws-otel-collector:amd"),
             logging=ecs.LogDriver.aws_logs(
                 stream_prefix='/otel-container',
                 log_group=logGroup
             ),
             essential=True,
             container_name="otel",
             memory_reservation_mib=512,
             #cpu=256,
            environment={
                "AWS_REGION": region,
                "AWS_PROMETHEUS_ENDPOINT": "https://aps-workspaces.us-east-1.amazonaws.com/workspaces/ws-5f8b1530-3388-4177-82af-eae1c6d54d57/api/v1/remote_write"
            },
            command=["--config=/etc/ecs/otel-config.yaml"]
         )
        ## Otel Container - END ##

        ## SERVICE ##
        postgres_service = ecs.Ec2Service(self, "Postgres",
        #postgres_service = ecs.FargateService(self, "Postgres",
            cluster=cluster,
            task_definition=postgres_task_definition,
            enable_execute_command=True,
            capacity_provider_strategies=[ecs.CapacityProviderStrategy(
                capacity_provider="amd-spot-api-capasity-provider", 
                weight=1
            )],
            service_name="postgres",
            security_groups=[pgmoviedb_sg],
            #service_connect_configuration=ecs.ServiceConnectProps(
            #    services=[ecs.ServiceConnectService(
            #        port_mapping_name="postgres",
            #        dns_name="pgmoviedb.api.local",
            #        discovery_name="postgres",
            #        port=5432,
            #    )
            #    ],
            #    #log_driver=ecs.LogDriver.aws_logs(stream_prefix="postgres-envoy"),
            #
            #), # service_connect_configuration
        )

        ## Cloud Map ##
        postgres_service.enable_cloud_map(name="pgmoviedb")

        ## AutoScaling for postgres ##
        scaling_postgres = postgres_service.auto_scale_task_count(max_capacity=10)
        scaling_postgres.scale_on_cpu_utilization("CpuScaling",
        target_utilization_percent=80,
        )
        # Scale on memory
        scaling_postgres.scale_on_memory_utilization("MemoryScaling",
        target_utilization_percent=80,
        )

        ## OUTPUT ###
        # Output the ARN of the ECS service to use in other Stacks.
        # - https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk/CfnOutput.html

        ## Postgres ##
        cdk.CfnOutput(self,"PostgresServiceArn",value=postgres_service.service_arn,export_name="PostgresServiceArn")

app=cdk.App()
PostgresStack(app, "PostgresStack", env=cdk.Environment(account=os.getenv("AWS_ACCOUNT_ID"), region=os.getenv("AWS_REGION")),)
app.synth()