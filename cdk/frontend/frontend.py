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
    aws_efs as efs,
    aws_route53 as route53,
    aws_route53_targets as route54_targets,
    aws_certificatemanager as acm
)
import os
from constructs import Construct
import aws_cdk as cdk
from aws_cdk.aws_ecr_assets import DockerImageAsset
import  cdk_ecr_deployment  as ecrdeploy

class FrontendStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        frontend_zone_name = "lmasu.co.za"
        frontend_fqdn = "ecs-api-frontend." + frontend_zone_name
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
        frontend_sg = ec2.SecurityGroup.from_security_group_id(self,"ImportedIndexSG",security_group_id=cdk.Fn.import_value("frontendSGID"))
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
            namespace_arn=cdk.Fn.import_value("ApiNamespaceArn"),
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
        # Import index virtual service
        index_virtual_service = appmesh.VirtualService.from_virtual_service_attributes(self,"ImportedindexVirtualService",mesh=mesh,virtual_service_name="index.api.local")
        ## Virtual Node ##
        frontend_node = appmesh.VirtualNode(self, "node",
            mesh=mesh,
            service_discovery=appmesh.ServiceDiscovery.dns("frontend.api.local"),
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
            backends=[appmesh.Backend.virtual_service(index_virtual_service)],
            virtual_node_name="frontend-node"
        )
        ## Virtual Service ##
        frontend_virtual_service = appmesh.VirtualService(self, "frontendVirtualService",
            virtual_service_provider=appmesh.VirtualServiceProvider.virtual_node(frontend_node),
            virtual_service_name="frontend" + "." + api_namespace.namespace_name
        )


        ######################
        ## FRONTEND SERVICE ## EC2 | BRIDGE | STATIC PORT MAPPING
        ######################
        frontend_task_definition = ecs.TaskDefinition(self, "FrontendTaskDef",
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
        proxy_configuration=ecs.AppMeshProxyConfiguration( 
            container_name="envoy", #App Mesh side card that will proxy the requests 
            properties=ecs.AppMeshProxyConfigurationProps(
                app_ports=[5000], # frontend application port
                proxy_ingress_port=15000, # side card default config
                proxy_egress_port=15001, # side card default config
                egress_ignored_i_ps=["169.254.170.2","169.254.169.254"], # side card default config
                ignored_uid=1337 # side card default config
            )
        )
        # appmesh-proxy-end ##
        #######################
        )

        ## Image ##
        # ECR
        # frontend_repo = ecr.Repository.from_repository_name(self,"FrontendRepo",repository_name="frontend.api.local")

        # Create log group for container logs
        logGroup = logs.LogGroup(self,"frontendLogGroup",
            log_group_name="/ecs/api/frontend",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=cdk.RemovalPolicy.DESTROY
        )

        ## Container ##
        frontend_container = frontend_task_definition.add_container("frontend",
           image=ecs.ContainerImage.from_registry("codesenju/frontend.api.local:amd"),
           # ECR
           #image=ecs.ContainerImage.from_ecr_repository(frontend_repo),
           logging=ecs.LogDrivers.aws_logs(stream_prefix="frontend-container",log_group=logGroup),
           memory_reservation_mib=512,
           #cpu=256,
           container_name="frontend", 
           
       )
        
        ## Port Mapping ##
        frontend_container.add_port_mappings(ecs.PortMapping(container_port=5000,name="frontend",host_port=5000))
        ########################################################
        ## App Mesh envoy proxy container configuration START ##
        frontend_envoy_container = frontend_task_definition.add_container(
            "FrontendServiceProxyContDef",
            image=ecs.ContainerImage.from_registry("public.ecr.aws/appmesh/aws-appmesh-envoy:v1.15.1.0-prod"),
            #image=ecs.ContainerImage.from_registry("public.ecr.aws/appmesh/aws-appmesh-envoy:arm64-v1.24.1.0-prod"),
            container_name="envoy",
            memory_reservation_mib=256,
            #cpu=256,
            environment={
                "AWS_REGION": region,
                "ENVOY_LOG_LEVEL": "debug",
                "ENABLE_ENVOY_STATS_TAGS": "1",
                "ENABLE_ENVOY_XRAY_TRACING": "1",
                "APPMESH_RESOURCE_ARN": frontend_node.virtual_node_arn
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
        
        frontend_envoy_container.add_ulimits(ecs.Ulimit(
            hard_limit=1048576, # case replication - 12040857631
            name=ecs.UlimitName.NOFILE,
            soft_limit=524288 # case replication - 12040857631
            )
        )
    
        ### Primary container needs to depend on envoy before it can be reached out
        frontend_container.add_container_dependencies(ecs.ContainerDependency(
               container=frontend_envoy_container,
               condition=ecs.ContainerDependencyCondition.HEALTHY
           )
        )
        # App Mesh envoy proxy container configuration END ##
        ######################################################

        # Enable app mesh Xray observability
        #ammmesh-xray-uncomment
        frontend_xray_container = frontend_task_definition.add_container(
             "FrontendXrayContainer",
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
    
        frontend_envoy_container.add_container_dependencies(ecs.ContainerDependency(
               container=frontend_xray_container,
               condition=ecs.ContainerDependencyCondition.START
           )
         )
        #ammmesh-xray-uncomment

        ## Otel Container - START ##
        frontend_otel_container = frontend_task_definition.add_container(
             "FrontendOtelContainer",
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
        
        ## Service ##
        frontend_service = ecs.Ec2Service(self, "Frontend",
            cluster=cluster,
            task_definition=frontend_task_definition,
            security_groups=[frontend_sg], # - RuntimeError: vpcSubnets, securityGroup(s) and assignPublicIp can only be used in AwsVpc networking mode
            enable_execute_command=True,
            capacity_provider_strategies=[ecs.CapacityProviderStrategy(
               # capacity_provider="spot-api-capasity-provider", 
                capacity_provider="amd-spot-api-capasity-provider", 
                weight=1,
                
            )],
            service_name="frontend",
            health_check_grace_period=cdk.Duration.seconds(300)

        )

        ###################################
        ## LOADBALANCING & ASUTO SCALING ##
        ###################################
    
        frontend_load_balancer = elbv2.ApplicationLoadBalancer(self, "FrontendLoadBalancer",vpc=vpc, internet_facing=True,security_group=elb_SG)
        frontend_listener = frontend_load_balancer.add_listener("FrontendListener",port=80)
        frontend_targetGroup = frontend_listener.add_targets("FrontendTargets",targets=[frontend_service],protocol=elbv2.ApplicationProtocol.HTTP)
        frontend_targetGroup.configure_health_check(path="/health")
        # Add a redirect from HTTP to HTTPS
        # frontend_listener.add_action("Redirect", action=elbv2.ListenerAction.redirect(port="443", protocol="HTTPS"))

        # Import the certificate
        #certificate = acm.Certificate.from_certificate_arn( self,"Certificate", os.getenv("CERT_ARN"))

        # Add an HTTPS listener
        #https_listener = frontend_load_balancer.add_listener("HTTPSListener", port=443, certificates=[certificate])

        # Add a target group for the HTTPS list
        # ener with a rule for the Host header
        #https_target_group = https_listener.add_targets("HTTPSTargets",
        #                           targets=[frontend_service],
        #                           protocol=elbv2.ApplicationProtocol.HTTPS,
        #                           priority=1, 
        #                           conditions=[elbv2.ListenerCondition.host_headers([frontend_fqdn])],                           
        #                           )
        

        # https_target_group.configure_health_check(path="/health")

        # https_listener.add_target_groups("HTTPSTargetGroup",target_groups=[https_target_group])
        

        ## AutoScaling for frontend ##
        scaling_frontend = frontend_service.auto_scale_task_count(max_capacity=20,min_capacity=3)
        scaling_frontend.scale_on_cpu_utilization("CpuScaling",
            target_utilization_percent=60
        )
        scaling_frontend.scale_on_memory_utilization("MemoryScaling",
            target_utilization_percent=60
        )

        # Creates an A Recod and associates it with skillsets_load_balancer
        #os.getenv("HOSTED_ZONE_ID")
        #full_hosted_zone_id = os.popen("aws route53 list-hosted-zones-by-name --dns-name 'lmasu.co.za' --query 'HostedZones[].Id' --out text").read()
        ## This code splits the input string at each occurrence of the ‘/’ character and takes the last element of the resulting list, which is the desired substring
        ## Using strip()to remove both leading and trailing whitespace 
        #hosted_zone_id = full_hosted_zone_id.split('/')[-1].strip() 

        #zone = route53.PublicHostedZone.from_public_hosted_zone_attributes(self,"ImportedHostedZone",zone_name=frontend_zone_name,hosted_zone_id=hosted_zone_id)
        #frontend_record = route53.ARecord(self, "FrontendRecord",
        #    zone=zone,
        #    target=route53.RecordTarget.from_alias(route54_targets.LoadBalancerTarget(frontend_load_balancer)),
        #    record_name=frontend_fqdn
        #)


        ## OUTPUT ###
        # Output the ARN of the ECS service to use in other Stacks.
        # - https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk/CfnOutput.html

        cdk.CfnOutput(self,"ApiFrontendDns",export_name="ApiFrontendDns",value=frontend_load_balancer.load_balancer_dns_name)

app=cdk.App()
FrontendStack(app, "FrontendStack", env=cdk.Environment(account=os.getenv("AWS_ACCOUNT_ID"), region=os.getenv("AWS_REGION")),)
app.synth()