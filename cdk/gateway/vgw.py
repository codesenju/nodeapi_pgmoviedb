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

class vgwStack(Stack):

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
        vgw_sg = ec2.SecurityGroup.from_security_group_id(self,"ImportedIndexSG",security_group_id=cdk.Fn.import_value("vgwSGID"))
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
        # Import frontend virtual service
        frontend_virtual_service = appmesh.VirtualService.from_virtual_service_attributes(self,"ImportedindexVirtualService",mesh=mesh,virtual_service_name="frontend.api.local")
        # We will create a App Mesh Virtual Gateway
        gateway = appmesh.VirtualGateway(self, "gateway",
            mesh=mesh,
            listeners=[appmesh.VirtualGatewayListener.http(
                port=5000,
                #connection_pool=appmesh.HttpConnectionPool(
                #    max_connections=20,
                #    max_pending_requests=20
                #)
            )],
            virtual_gateway_name="mesh_vgw"
        )
        gateway.add_gateway_route("gateway-route-http",
            route_spec=appmesh.GatewayRouteSpec.http(
                route_target=frontend_virtual_service,
                #match=appmesh.HttpGatewayRouteMatch(
                #    path=appmesh.HttpGatewayRoutePathMatch.regex("/")
                #)

            ),
            gateway_route_name="mesh_frontend_route"
        )

        ######################
        ## vgw SERVICE ## EC2 | BRIDGE | STATIC PORT MAPPING
        ######################
        vgw_task_definition = ecs.TaskDefinition(self, "vgwTaskDef",
        execution_role=task_execution_role, 
        task_role=task_role,
        network_mode=ecs.NetworkMode.AWS_VPC, # I need to investigate why bridge network mode is giving me issues - I keep getting task failed ELB health checks
        compatibility=ecs.Compatibility.EC2_AND_FARGATE,
        cpu="1024",
        memory_mib="2048",
        # Frgate runtime settings
        #runtime_platform=ecs.RuntimePlatform(                          # FOR FARGATE
        #    operating_system_family=ecs.OperatingSystemFamily.LINUX,
        #    cpu_architecture=ecs.CpuArchitecture.ARM64
        #    ),
        #
        #########################
        ## appmesh-proxy-start ##
        #proxy_configuration=ecs.AppMeshProxyConfiguration( 
        #    container_name="envoy", #App Mesh side card that will proxy the requests 
        #    properties=ecs.AppMeshProxyConfigurationProps(
        #        app_ports=[5000], # vgw application port
        #        proxy_ingress_port=15000, # side card default config
        #        proxy_egress_port=15001, # side card default config
        #        egress_ignored_i_ps=["169.254.170.2","169.254.169.254"], # side card default config
        #        ignored_uid=1337 # side card default config
        #    )
        #)
        # appmesh-proxy-end ##
        #######################
        )

        ## Image ##
        # ECR
        # vgw_repo = ecr.Repository.from_repository_name(self,"vgwRepo",repository_name="vgw.api.local")

        # Create log group for container logs
        logGroup = logs.LogGroup(self,"vgwLogGroup",
            log_group_name="/ecs/api/vgw",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=cdk.RemovalPolicy.DESTROY
        )

        ########################################################
        ## App Mesh envoy proxy container configuration START ##
        vgw_envoy_container = vgw_task_definition.add_container(
            "GatewayServiceProxyContDef",
            #image=ecs.ContainerImage.from_registry("public.ecr.aws/appmesh/aws-appmesh-envoy:v1.18.3.0-prod"),
            image=ecs.ContainerImage.from_registry("public.ecr.aws/appmesh/aws-appmesh-envoy:arm64-v1.24.2.0-prod"),
            container_name="envoy",
            memory_reservation_mib=512,
            cpu=256,
            environment={
                "AWS_REGION": region,
                "ENVOY_LOG_LEVEL": "debug",
                "ENABLE_ENVOY_STATS_TAGS": "1",
                "ENABLE_ENVOY_XRAY_TRACING": "1",
                "APPMESH_RESOURCE_ARN": gateway.virtual_gateway_arn
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
        
        vgw_envoy_container.add_ulimits(ecs.Ulimit(
            hard_limit=15000,
            name=ecs.UlimitName.NOFILE,
            soft_limit=15000
            )
        )
        vgw_envoy_container.add_port_mappings(ecs.PortMapping(container_port=5000,name="envoy"))
        # App Mesh envoy proxy container configuration END ##
        ######################################################

        # Enable app mesh Xray observability
        #ammmesh-xray-uncomment
        vgw_xray_container = vgw_task_definition.add_container(
             "vgwXrayContainer",
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
        
        vgw_envoy_container.add_container_dependencies(ecs.ContainerDependency(
               container=vgw_xray_container,
               condition=ecs.ContainerDependencyCondition.START
           )
         )
        #ammmesh-xray-uncomment

        ## Otel Container - START ##
        #vgw_otel_container = vgw_task_definition.add_container(
        #     "vgwOtelContainer",
        #     image=ecs.ContainerImage.from_registry("587878432697.dkr.ecr.us-east-1.amazonaws.com/aws-otel-collector:cx"),
        #     logging=ecs.LogDriver.aws_logs(
        #         stream_prefix='/otel-container',
        #         log_group=logGroup
        #     ),
        #     essential=True,
        #     container_name="otel",
        #     memory_reservation_mib=512,
        #     cpu=256,
        #    environment={
        #        "AWS_REGION": region,
        #        "AWS_PROMETHEUS_ENDPOINT": "https://aps-workspaces.us-east-1.amazonaws.com/workspaces/ws-5f8b1530-3388-4177-82af-eae1c6d54d57/api/v1/remote_write"
        #    },
        #    command=["--config=/etc/ecs/otel-config.yaml"]
        # )
        ### Otel Container - END ##
        
        ## Service ##
        vgw_service = ecs.Ec2Service(self, "mesh_vgw",
            cluster=cluster,
            task_definition=vgw_task_definition,
            security_groups=[vgw_sg], # - RuntimeError: vpcSubnets, securityGroup(s) and assignPublicIp can only be used in AwsVpc networking mode
            enable_execute_command=True,
            capacity_provider_strategies=[ecs.CapacityProviderStrategy(
               # capacity_provider="spot-api-capasity-provider", 
                capacity_provider="spot-api-capasity-provider", 
                weight=1,
                
            )],
            service_name="mesh_vgw",
            health_check_grace_period=cdk.Duration.seconds(500000)

        )

        ###################################
        ## LOADBALANCING & ASUTO SCALING ##
        ###################################
    
        vgw_load_balancer = elbv2.ApplicationLoadBalancer(self, "vgwLoadBalancer",vpc=vpc, internet_facing=True,security_group=elb_SG)
        vgw_listener = vgw_load_balancer.add_listener("vgwListener",port=80)
        vgw_targetGroup = vgw_listener.add_targets("vgwTargets",targets=[vgw_service],protocol=elbv2.ApplicationProtocol.HTTP)
        vgw_targetGroup.configure_health_check(path="/health")
    

        ## AutoScaling for vgw ##
        scaling_vgw = vgw_service.auto_scale_task_count(max_capacity=10)
        scaling_vgw.scale_on_cpu_utilization("CpuScaling",
            target_utilization_percent=60
        )

        ## OUTPUT ###
        # Output the ARN of the ECS service to use in other Stacks.
        # - https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk/CfnOutput.html

        cdk.CfnOutput(self,"VgwElbEndpoint",export_name="VgwApiElbEndpoint",value=vgw_load_balancer.load_balancer_dns_name)

app=cdk.App()
vgwStack(app, "vgwStack", env=cdk.Environment(account=os.getenv("AWS_ACCOUNT_ID"), region=os.getenv("AWS_REGION")),)
app.synth()