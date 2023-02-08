#!/usr/bin/env python3
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

       # Create Security Group
        security_group = ec2.SecurityGroup.from_security_group_id(self, "ImportedSG", os.getenv("SG"))
        # Create security group for postgres
        Postgres_SG = ec2.SecurityGroup(self, "Postgres_SG",vpc=vpc,security_group_name="Postgres_SG",allow_all_outbound=False)
        Postgres_SG.add_ingress_rule(ec2.Peer.any_ipv4(),ec2.Port.tcp(5432),description="Allow inbound 5000 for postgres db from Nodeapi")
        Postgres_SG.add_egress_rule(ec2.Peer.any_ipv4(),ec2.Port.tcp(2049),description="Allow outbound 2049 for postgres db to anywhere")
        Postgres_SG.add_egress_rule(ec2.Peer.any_ipv4(),ec2.Port.tcp(443),description="Allow outbound 443")


        # Create security group for postgres EFS Filesystem to allow inbound 2049
        efs_SG = ec2.SecurityGroup(self, "EFS_allowInbound2049_SG",vpc=vpc,security_group_name="PostgresEFS_SG",allow_all_outbound=False)
        efs_SG.add_ingress_rule(ec2.Peer.any_ipv4(),ec2.Port.tcp(2049),description="EFS Filesystem to allow inbound 2049")
        #postgresEFS_SG.add_egress_rule(ec2.Peer.any_ipv4(),ec2.Port.tcp(443),description="Allow outbound 443")
    
        # Import IAM task execution role
        existing_task_execution_role_name = "ecsTaskExecutionRole" 
        existing_task_execution_role_arn = f'arn:aws:iam::{account}:role/{existing_task_execution_role_name}'
        task_execution_role = iam.Role.from_role_arn(self, 'ImportedTaskExecutionRole', role_arn=existing_task_execution_role_arn)

        # Import IAM task role
        existing_task_role_name = "000A_ecsExecTaskRole"
        existing_task_role_arn = f'arn:aws:iam::{account}:role/{existing_task_role_name}'
        task_role = iam.Role.from_role_arn(self, 'ImportedEcsExecTaskRole', role_arn=existing_task_role_arn)

        # Import Namespace api.local
        namespace_id = os.getenv("NAMESPACE_ID")
        namespace_name = "api.local"
        api_namespace= servicediscovery.PrivateDnsNamespace.from_private_dns_namespace_attributes(self, "ImportedNamespace",
            namespace_arn=f"arn:aws:servicediscovery:{region}:{account}:namespace/{namespace_id}",
            namespace_id=str(namespace_id),
            namespace_name=namespace_name
        )

        # Import ECS Cluster
        cluster = ecs.Cluster.from_cluster_attributes(self, "ImportedCluster",
            cluster_name=f"{ecs_cluster_name}",
            security_groups=[security_group],
            vpc=vpc,
            default_cloud_map_namespace=api_namespace
        )
    

        ######################
        ## POSTGRES SERVICE ##
        ######################
        # Create the EFS file system
        efs_file_system = efs.FileSystem(self, "PG_EFSFileSystem",
        vpc=vpc,
        security_group=efs_SG,
        vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
        removal_policy=cdk.RemovalPolicy.DESTROY
        )
       

        # Import FileSystem
        #imported_fs = efs.FileSystem.from_file_system_attributes(self, "ImportedFS", file_system_id="fs-03048c4a93edd5d09",security_group=postgresEFS_SG)

        # Create volume
        pg_volume = ecs.Volume(name="PGDATA",efs_volume_configuration={
                   "file_system_id": efs_file_system.file_system_id
        })

        # Create the EFS mount point
        pg_efs_mount_point = ecs.MountPoint(source_volume=pg_volume.name, 
                                        container_path="/var/lib/postgresql/data",
                                        read_only=False)

        # Define the task definition for the Postgres service
        postgres_task_definition = ecs.FargateTaskDefinition(self, "PostgresTaskDef",
        execution_role=task_execution_role,
        runtime_platform=ecs.RuntimePlatform(
            operating_system_family=ecs.OperatingSystemFamily.LINUX,
            cpu_architecture=ecs.CpuArchitecture.ARM64
            ),
        #volumes=[pg_volume]
        )
        postgres_repo = ecr.Repository.from_repository_name(self,"PostgresRepo",repository_name="pgmoviedb.api.local")
        postgres_container = postgres_task_definition.add_container(
            "Postgres",
            #image=ecs.ContainerImage.from_docker_image_asset(pgmoviedb_image_asset),
            #image=ecs.ContainerImage.from_registry(f"{account}.dkr.ecr.{region}.amazonaws.com/postgres.api.local:arm"),
            image=ecs.ContainerImage.from_ecr_repository(postgres_repo),
            environment={
                "POSTGRES_DB": "movie",
                "POSTGRES_PASSWORD": "12345"
            },
            logging=ecs.LogDrivers.aws_logs(stream_prefix="postgres"),
            memory_limit_mib=512,
            cpu=256,
            
        )


        #postgres_container.add_mount_points(pg_efs_mount_point)
        
        
        postgres_container.add_port_mappings(ecs.PortMapping(container_port=5432,name="postgres"))
        
        postgres_service = ecs.FargateService(self, "Postgres",
            cluster=cluster,
            task_definition=postgres_task_definition,
            enable_execute_command=True,
            security_groups=[Postgres_SG],
            service_connect_configuration=ecs.ServiceConnectProps(
                services=[ecs.ServiceConnectService(
                    port_mapping_name="postgres",
                    dns_name="pgmoviedb.api.local",
                    discovery_name="postgres",
                    port=5432,
                )
                ],
                #log_driver=ecs.LogDriver.aws_logs(stream_prefix="postgres-envoy"),
            
            ), # service_connect_configuration
        )
        #postgres_service.enable_cloud_map(name="pgmoviedb")

        ###################################
        ## LOADBALANCING & ASUTO SCALING ##
        ###################################
        
        # AutoScaling for postgres
        scaling_postgres = postgres_service.auto_scale_task_count(max_capacity=10)
        scaling_postgres.scale_on_cpu_utilization("CpuScaling",
            target_utilization_percent=80
        )


app=cdk.App()
NodeApiStack(app, "NodeApiStack", env=cdk.Environment(account=os.getenv("AWS_ACCOUNT_ID"), region=os.getenv("AWS_REGION")),)
app.synth()