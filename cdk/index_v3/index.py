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

class IndexStack(Stack):

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


        # Import Security groups
        security_group = ec2.SecurityGroup.from_security_group_id(self,"ImporteDefaultApiClusterSG",security_group_id=cdk.Fn.import_value("DefaultAPIClusterSG"))
        index_sg = ec2.SecurityGroup.from_security_group_id(self,"ImportedIndexSG",security_group_id=cdk.Fn.import_value("indexSGID"))
        elb_SG = ec2.SecurityGroup.from_security_group_id(self,"importedelbSG",security_group_id=cdk.Fn.import_value("elbSGID")) 

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


        ###################################
        ## Create the App Mesh resources ##
        ###################################
        # Import mesh
        mesh = appmesh.Mesh.from_mesh_arn(self,"ImportedEcsApiMesh",mesh_arn=cdk.Fn.import_value("EcsApiMeshArn"))
        # Import nodeapi virtual service
        nodeapi_virtual_service = appmesh.VirtualService.from_virtual_service_attributes(self,"ImportedNodeapiVirtualService",mesh=mesh,virtual_service_name="nodeapi.api.local")
        ## Virtual Node ##
        index_node = appmesh.VirtualNode(self, "node",
            mesh=mesh,
            service_discovery=appmesh.ServiceDiscovery.dns("index.api.local"),
            listeners=[appmesh.VirtualNodeListener.http(
                port=5000,
                health_check=appmesh.HealthCheck.http(
                    healthy_threshold=3,
                    interval=cdk.Duration.seconds(5),
                    path="/health",
                    timeout=cdk.Duration.seconds(2),
                    unhealthy_threshold=2
                ),
                timeout=appmesh.HttpTimeout(
                    idle=cdk.Duration.seconds(5)
                )
            )],
            access_log=appmesh.AccessLog.from_file_path("/dev/stdout"),
            backends=[appmesh.Backend.virtual_service(nodeapi_virtual_service)],
            virtual_node_name="index-node"
        )
        ## Virtual Service ##
        index_virtual_service = appmesh.VirtualService(self, "IndexVirtualService",
            virtual_service_provider=appmesh.VirtualServiceProvider.virtual_node(index_node),
            virtual_service_name="index" + "." + api_namespace.namespace_name
        )

   
        ######################
        ## INDEX SERVICE ##### EC2 | BRIDGE | DYNAMIC PORT MAPPINGS OR FARGATE
        ######################
        
        ## Task Definition ##
        index_task_definition = ecs.TaskDefinition(self, "IndexTaskDef",
        execution_role=task_execution_role, 
        task_role=task_role,
        network_mode=ecs.NetworkMode.AWS_VPC,
        compatibility=ecs.Compatibility.EC2_AND_FARGATE,
        cpu="1024",
        memory_mib="2048",
        #runtime_platform=ecs.RuntimePlatform(
        #    operating_system_family=ecs.OperatingSystemFamily.LINUX,
        #    cpu_architecture=ecs.CpuArchitecture.ARM64
        #    ),
        #########################
        ## appmesh-proxy-start ##
        proxy_configuration=ecs.AppMeshProxyConfiguration( 
            container_name="envoy", #App Mesh side card that will proxy the requests 
            properties=ecs.AppMeshProxyConfigurationProps(
                app_ports=[5000], # index application port
                proxy_ingress_port=15000, # side card default config
                proxy_egress_port=15001, # side card default config
                egress_ignored_i_ps=["169.254.170.2","169.254.169.254"], # side card default config
                ignored_uid=1337 # side card default config
            )
        )
        ## appmesh-proxy-end ##
        #######################
        )

        ## Image ##
        # ECR
        # index_repo = ecr.Repository.from_repository_name(self,"IndexRepo",repository_name="index.api.local")

        # Create log group for container logs
        logGroup = logs.LogGroup(self,"indexLogGroup",
            log_group_name="/ecs/api/index_v3",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=cdk.RemovalPolicy.DESTROY
        )

        ## Container ##
        index_container = index_task_definition.add_container(
           "index",
           # ECR
           #image=ecs.ContainerImage.from_ecr_repository(index_repo),
           image=ecs.ContainerImage.from_registry("codesenju/index.api.local:amd_v3"),
           logging=ecs.LogDrivers.aws_logs(stream_prefix="/index-container",log_group=logGroup),
           memory_reservation_mib=512,
           cpu=256,
           container_name="index",                 
       )
        
        ## Port Mapping ##
        index_container.add_port_mappings(ecs.PortMapping(container_port=5000,name="index"))

        ########################################################
        ## App Mesh envoy proxy container configuration START ##
        index_envoy_container = index_task_definition.add_container(
            "Index_v3EnvoyContainer",
            image=ecs.ContainerImage.from_registry("public.ecr.aws/appmesh/aws-appmesh-envoy:v1.25.1.0-prod"),
            #image=ecs.ContainerImage.from_registry("public.ecr.aws/appmesh/aws-appmesh-envoy:arm64-v1.24.2.0-prod"),
            container_name="envoy",
            #memory_reservation_mib=512,
            #cpu=256,
            environment={
                "AWS_REGION": region,
                "ENVOY_LOG_LEVEL": "debug",
                "ENABLE_ENVOY_STATS_TAGS": "1",
                "ENABLE_ENVOY_XRAY_TRACING": "1",
                "APPMESH_RESOURCE_ARN": index_node.virtual_node_arn
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
        
        index_envoy_container.add_ulimits(ecs.Ulimit(
            hard_limit=1048576, # case replication - 12040857631
            name=ecs.UlimitName.NOFILE,
            soft_limit=524288 # case replication - 12040857631
            )
        )

        ## Primary container needs to depend on envoy before it can be reached out
        index_container.add_container_dependencies(ecs.ContainerDependency(
               container=index_envoy_container,
               condition=ecs.ContainerDependencyCondition.HEALTHY
           )
        )
        ## App Mesh envoy proxy container configuration END ##
        ######################################################

        # Enable app mesh Xray observability
        #ammmesh-xray-uncomment
        xray_container = index_task_definition.add_container(
             "Index_v3XrayContainer",
             image=ecs.ContainerImage.from_registry("amazon/aws-xray-daemon"),
             logging=ecs.LogDriver.aws_logs(
                 stream_prefix='/xray-container',
                 log_group=logGroup
             ),
             essential=True,
             container_name="xray",
             memory_reservation_mib=512,
             cpu=256,
             user="1337",
            environment={
                "AWS_REGION": region,
            },
         )
    
        index_envoy_container.add_container_dependencies(ecs.ContainerDependency(
               container=xray_container,
               condition=ecs.ContainerDependencyCondition.START
           )
         )
        #ammmesh-xray-uncomment

        ## Otel Container - START ##
        frontend_otel_container = index_task_definition.add_container(
             "Index_v3OtelContainer",
             image=ecs.ContainerImage.from_registry("codesenju/aws-otel-collector:amd"),
             logging=ecs.LogDriver.aws_logs(
                 stream_prefix='/otel-container',
                 log_group=logGroup
             ),
             essential=True,
             container_name="otel",
             memory_reservation_mib=512,
             cpu=256,
            environment={
                "AWS_REGION": region,
                "AWS_PROMETHEUS_ENDPOINT": "https://aps-workspaces.us-east-1.amazonaws.com/workspaces/ws-5f8b1530-3388-4177-82af-eae1c6d54d57/api/v1/remote_write"
            },
            command=["--config=/etc/ecs/otel-config.yaml"]
         )
        ## Otel Container - END ##

        ## Service ##
        index_service = ecs.Ec2Service(self, "Index_v3",
            cluster=cluster,
            task_definition=index_task_definition,
            enable_execute_command=True,
            capacity_provider_strategies=[ecs.CapacityProviderStrategy(
                capacity_provider="amd-spot-api-capasity-provider", 
                weight=1,
            )],
            service_name="index_v3",
            security_groups=[index_sg],
        )
        ## CloudMap ##
        index_service.enable_cloud_map(name="index_v3")
        
        ###################################
        ## LOADBALANCING & ASUTO SCALING ##
        ###################################
    
        #index_load_balancer = elbv2.ApplicationLoadBalancer(self, "IndexLoadBalancer",vpc=vpc, internet_facing=True,security_group=elb_SG)
        #index_listener = index_load_balancer.add_listener("IndexListener",port=80)
        #index_targetGroup = index_listener.add_targets("IndexTargets",targets=[index_service],protocol=elbv2.ApplicationProtocol.HTTP)
        #index_targetGroup.configure_health_check(path="/")

        ## OUTPUT ###
        # Output the ARN of the ECS service to use in other Stacks.
        # - https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk/CfnOutput.html

        #cdk.CfnOutput(self,"indexVSname",value=index_virtual_service.virtual_service_name,export_name="indexVSName")
        cdk.CfnOutput(self,"index_v3ServiceArn",value=index_service.service_arn,export_name="index_v3ServiceArn")


app=cdk.App()
IndexStack(app, "IndexStack", env=cdk.Environment(account=os.getenv("AWS_ACCOUNT_ID"), region=os.getenv("AWS_REGION")),)
app.synth()