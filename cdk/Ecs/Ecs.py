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
    aws_ssm as ssm,
    aws_servicediscovery as servicediscovery
)
import os
from constructs import Construct
import aws_cdk as cdk
from aws_cdk.aws_ecr_assets import DockerImageAsset

class EcsClusterStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Get  environment variable
        cluster_name = 'api'

        # Import existing VPC
        vpc = ec2.Vpc.from_lookup(
            self, "ImportedVpc",
            vpc_name='VpcInfraStack/ApiProjectVpc'
        )

        # Create an ECS cluster in the imported VPC
        cluster = ecs.Cluster(self, "ApiEcsCluster", vpc=vpc,
        cluster_name=cluster_name,
        container_insights=True,
        enable_fargate_capacity_providers=True,
        )
        cluster.add_default_cloud_map_namespace(name="api.local",use_for_service_connect=True)

        # Create security group
        security_group = ec2.SecurityGroup(self,"amdAPIClusterSG",vpc=vpc,allow_all_outbound=False,description="amd api cluster security group",security_group_name="amdAPIClusterSG")

        # Create mesh
        mesh = appmesh.Mesh(self,"EcsApiMesh",mesh_name="ApiEcs",egress_filter=appmesh.MeshFilterType.ALLOW_ALL)
        
        # Configure the ECS agent to drain Spot Instances upon catching a Spot Interruption notice from instance metadata
        user_data = ec2.UserData.custom(
            #f"#!/bin/bash\n echo ECS_CLUSTER={os.getenv('ECS_CLUSTER_NAME')} >> /etc/ecs/ecs.config"
            f"#!/bin/bash\n echo ECS_CLUSTER={cluster_name} >> /etc/ecs/ecs.config\n echo ECS_ENABLE_SPOT_INSTANCE_DRAINING=true >> /etc/ecs/ecs.config \n echo ECS_IMAGE_PULL_BEHAVIOR=always >> /etc/ecs/ecs.config "
        )

        # user_data=ec2.UserData.add_commands(f"echo ECS_CLUSTER={os.getenv('ECS_CLUSTER_NAME')}  >> /etc/ecs/ecs.config","echo ECS_ENABLE_SPOT_INSTANCE_DRAINING=true >> /etc/ecs/ecs.config"),
        api_asg_sg=ec2.SecurityGroup(self, "LaunchTemplateSG",vpc=vpc, security_group_name="api-sg",allow_all_outbound=True)
        api_asg_sg.add_ingress_rule(ec2.Peer.any_ipv4(),ec2.Port.tcp(5000),description="Allow inbound 5000 from LB")
        # Create custom launch template
        launch = ec2.LaunchTemplate(self, "NodeapiLaunchTemplate",
        launch_template_name="nodeapi-launch-template",
        security_group=api_asg_sg,
        user_data=user_data,
        role=iam.Role.from_role_name(self, "ecsworkshopRole","ecsworkshop-admin"),
        machine_image=ecs.EcsOptimizedImage.amazon_linux2(ecs.AmiHardwareType.ARM),
        #machine_image=ecs.EcsOptimizedImage.amazon_linux2(),
        #instance_type=ec2.InstanceType("t2.xlarge"),
        instance_type=ec2.InstanceType("a1.2xlarge"),
        )

        amd_launch = ec2.LaunchTemplate(self, "AmdNodeapiLaunchTemplate",
        launch_template_name="amd-nodeapi-launch-template",
        security_group=api_asg_sg,
        user_data=user_data,
        role=iam.Role.from_role_name(self, "amd-ecsworkshopRole","ecsworkshop-admin"),
        machine_image=ecs.EcsOptimizedImage.amazon_linux2(ecs.AmiHardwareType.STANDARD),
        #machine_image=ecs.EcsOptimizedImage.amazon_linux2(),
        #instance_type=ec2.InstanceType("t2.xlarge"),
        instance_type=ec2.InstanceType("m5.large"),
        )

        ## add customized capacity. Be sure to start the Amazon ECS-optimized AMI.
        auto_scaling_group = autoscaling.AutoScalingGroup(self, "ASG",
            vpc=vpc,
            launch_template=launch, # Amazon ECS-optimized AMI in launch type already defined
            max_capacity=4,
            min_capacity=0,
            desired_capacity=0,
            new_instances_protected_from_scale_in=True,
            auto_scaling_group_name="api-asg"
        )

        ## Creates the Capasity provider and adds it to the ECS cluster
        capacity_provider = ecs.AsgCapacityProvider(self, "AsgCapacityProvider",
           auto_scaling_group=auto_scaling_group,
           enable_managed_scaling=True,
           enable_managed_termination_protection=True,
           capacity_provider_name="api-capasity-provider"
        )
        cluster.add_asg_capacity_provider(capacity_provider)


        ##########################
        ## ARM - SPOT INSTANCES ##
        #########################
        ## add customized capacity. Be sure to start the Amazon ECS-optimized AMI.
        arm_spot_auto_scaling_group = autoscaling.AutoScalingGroup(self, "SPOT_ASG",
            vpc=vpc,
            # launch_template=launch, # Amazon ECS-optimized AMI in launch type already defined
            max_capacity=4,
            min_capacity=0,
            desired_capacity=0,
            new_instances_protected_from_scale_in=True,
            auto_scaling_group_name="arm-spot-api-asg",
            #spot_price="0.0735",
            # Enable the Automated Spot Draining support for Amazon ECS
            #spot_instance_draining=True,
            mixed_instances_policy=autoscaling.MixedInstancesPolicy(
            launch_template=launch,
            instances_distribution=autoscaling.InstancesDistribution(
                on_demand_base_capacity=0,
                on_demand_percentage_above_base_capacity=0,
                spot_allocation_strategy=autoscaling.SpotAllocationStrategy.LOWEST_PRICE),
            launch_template_overrides=[autoscaling.LaunchTemplateOverrides(instance_type=ec2.InstanceType("c6gn.xlarge"),launch_template=launch),
            autoscaling.LaunchTemplateOverrides(instance_type=ec2.InstanceType("c6gn.2xlarge"),launch_template=launch)
            ]
        
           ),
           
        )
        ## Creates the Capasity provider and adds it to the ECS cluster - arm
        arm_spot_capacity_provider = ecs.AsgCapacityProvider(self, "SpotAsgCapacityProvider",
           auto_scaling_group=arm_spot_auto_scaling_group,
           enable_managed_scaling=True,
           enable_managed_termination_protection=True,
           capacity_provider_name="spot-api-capasity-provider",
           
        )
        cluster.add_asg_capacity_provider(arm_spot_capacity_provider)

        ###################################
        ##  AMD -  SPOT INSTANCES ##
        ###################################
        ## add customized capacity. Be sure to start the Amazon ECS-optimized AMI.
        amd_spot_auto_scaling_group = autoscaling.AutoScalingGroup(self, "AMD_SPOT_ASG",
            vpc=vpc,
            # launch_template=launch, # Amazon ECS-optimized AMI in launch type already defined
            max_capacity=2,
            min_capacity=0,
            desired_capacity=0,
            new_instances_protected_from_scale_in=True,
            auto_scaling_group_name="amd-spot-api-asg",
            #spot_price="0.0735",
            # Enable the Automated Spot Draining support for Amazon ECS
            #spot_instance_draining=True,
            mixed_instances_policy=autoscaling.MixedInstancesPolicy(
            launch_template=amd_launch,
            instances_distribution=autoscaling.InstancesDistribution(
                on_demand_base_capacity=0,
                on_demand_percentage_above_base_capacity=0,
                spot_allocation_strategy=autoscaling.SpotAllocationStrategy.LOWEST_PRICE),
            launch_template_overrides=[autoscaling.LaunchTemplateOverrides(instance_type=ec2.InstanceType("m5.xlarge"),launch_template=amd_launch),
            autoscaling.LaunchTemplateOverrides(instance_type=ec2.InstanceType("m5.2xlarge"),launch_template=amd_launch)
            ]
           ),  
        )

        ## Creates the Capasity provider and adds it to the ECS cluster - amd
        amd_spot_capacity_provider = ecs.AsgCapacityProvider(self, "AmdSpotAsgCapacityProvider",
           auto_scaling_group=amd_spot_auto_scaling_group ,
           enable_managed_scaling=True,
           enable_managed_termination_protection=True,
           capacity_provider_name="amd-spot-api-capasity-provider",
           
        )
        cluster.add_asg_capacity_provider(amd_spot_capacity_provider)

        ## Outpute ##
        # Output namespace arn, name and id to be used in other stacks.
        cdk.CfnOutput(self,"ApiNamespaceArn",value=cluster.default_cloud_map_namespace.namespace_arn,export_name="ApiNamespaceArn")
        cdk.CfnOutput(self,"ApiNamespaceName",value=cluster.default_cloud_map_namespace.namespace_name,export_name="ApiNamespaceName")
        cdk.CfnOutput(self,"ApiNamespaceId",value=cluster.default_cloud_map_namespace.namespace_id,export_name="ApiNamespaceId")
        cdk.CfnOutput(self,"amdApiClusterSGID",value=security_group.security_group_id,export_name="amdApiClusterSGID")
        cdk.CfnOutput(self,"EcsApiMeshArn",value=mesh.mesh_arn,export_name="EcsApiMeshArn")

app = cdk.App()

# ECS Cluster
EcsClusterStack(app, "EcsClusterStack", env=cdk.Environment(account=os.getenv('AWS_ACCOUNT_ID'), region=os.getenv('AWS_REGION')),)
app.synth()