# AppMesh setup the easy way.
#### <span style="color: red">Important!</span> VirtualService names should be the same with k8s service names. You will probably get bellow error if not set as mentioned with pod to pod communication:
####```Error: HTTP Status code 404 not found```
## 1.1 Set env variables
```bash
export CLUSTER_NAME=<eks-cluster-name>
export AWS_REGION=$(aws configure get region)
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export IAM_APP_MESH=001_AWSAppMeshK8sControllerIAM
```
## 1.2
```bash
export APP_NS=api
# Create namespace for applications.
kubectl apply -f api-namespace.yaml
```
## 2. Create namespace
```bash
kubectl create ns appmesh-system
```
## 3. Download the IAM policy for AWS App Mesh Kubernetes Controller

```bash
curl -o ${IAM_APP_MESH}.json https://raw.githubusercontent.com/aws/aws-app-mesh-controller-for-k8s/master/config/iam/controller-iam-policy.json
```

## 4. Create an IAM policy
```bash
POLICY_ARN=$(aws iam create-policy \
    --policy-name ${IAM_APP_MESH} \
    --policy-document file://${IAM_APP_MESH}.json --query Policy.Arn --output text)
```

## 5. Create an IAM role for service account for the App Mesh Kubernetes controller, use the ARN from the step above.
```bash
eksctl create iamserviceaccount --cluster $CLUSTER_NAME \
    --namespace appmesh-system \
    --name appmesh-controller \
    --role-name $IAM_APP_MESH \
    --attach-policy-arn arn:aws:iam::$AWS_ACCOUNT_ID:policy/$IAM_APP_MESH  \
    --override-existing-serviceaccounts \
    --approve
```

## 6. Deploy appmesh-controller
```bash
helm upgrade -i appmesh-controller eks/appmesh-controller \
    --namespace appmesh-system \
    --set region=$AWS_REGION \
    --set serviceAccount.create=false \
    --set serviceAccount.name=appmesh-controller
```
#### 6.1 <span style="color: red">Running on ARM Based Instances</span>
```bash
helm upgrade -i appmesh-controller eks/appmesh-controller \
    --namespace appmesh-system \
    --set region=$AWS_REGION \
    --set serviceAccount.create=false \
    --set serviceAccount.name=appmesh-controller \
    --set image.tag=v1.10.0-linux_arm64  \
    --set log.level=debug
```

### 6.2 Enable X-Ray Tracing
```bash
helm upgrade -i appmesh-controller eks/appmesh-controller \
    --namespace appmesh-system \
    --set region=$AWS_REGION \
    --set serviceAccount.create=false \
    --set serviceAccount.name=appmesh-controller \
    --set image.tag=v1.10.0-linux_arm64 \
    --set tracing.enabled=true \
    --set tracing.provider=x-ray \
    --set log.level=debug
```

### 6.3 Install with nodeSelector
```bash
helm upgrade -i appmesh-controller eks/appmesh-controller \
    --namespace appmesh-system \
    --set region=$AWS_REGION \
    --set serviceAccount.create=false \
    --set serviceAccount.name=appmesh-controller \
    --set image.tag=v1.10.0-linux_arm64 \
    --set tracing.enabled=true \
    --set tracing.provider=x-ray \
    --set log.level=debug \
    --set nodeSelector.karpenter\\.sh/provisioner-name=arm-fleet \
    --wait
```
### Uninstall App Mesh Controller
```bash
helm uninstall  appmesh-controller --namespace appmesh-system
```
### 6.2 <span style="color: red">Note!</span> Make sure that the Envoy proxies have the following [IAM policies](https://raw.githubusercontent.com/aws/aws-app-mesh-controller-for-k8s/master/config/iam/envoy-iam-policy.json) attached for the Envoy to authenticate with AWS App Mesh and fetch it's configuration.
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "appmesh:StreamAggregatedResources"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "acm:ExportCertificate",
                "acm-pca:GetCertificateAuthorityCertificate"
            ],
            "Resource": "*"
        }
    ]
}
```
## 7. There are 2 ways you can attach the above policy to the Envoy Pod
*I'm only covering the first option.*
### A) With IRSA
#### Set env variables
```bash
ENVOY_IAM=001_AWSAppMeshEnvoyIAM
```
#### Download the Envoy IAM policy
```bash
curl -o ${ENVOY_IAM}.json https://raw.githubusercontent.com/aws/aws-app-mesh-controller-for-k8s/master/config/iam/envoy-iam-policy.json
```

#### Create an IAM policy
```bash
ENVOY_POLICY_ARN=$(aws iam create-policy \
    --policy-name ${ENVOY_IAM} \
    --policy-document file://${ENVOY_IAM}.json --query Policy.Arn --output text)
```
*If your Mesh enabled applications are already using IRSA then you can attach the above policy to the role belonging to the existing IRSA or you can edit the Trust Relationship of the existing iam role which has this envoy policy so that some other service account in your mesh can also assume this role.*

**If not then you can create a service account for your application namespace and use the ARN from the step above. Ensure that Application Namespace already exists**
```bash
# ApplicationNamespaceName to which Envoy gets Injected
export APP_NS=***
```
```bash
eksctl create iamserviceaccount --cluster $CLUSTER_NAME \
    --namespace $APP_NS \
    --name envoy-proxy \
    --role-name $ENVOY_IAM \
    --attach-policy-arn arn:aws:iam::$AWS_ACCOUNT_ID:policy/$ENVOY_IAM \
    --override-existing-serviceaccounts \
    --approve
```
### [~~B) Without IRSA~~](https://github.com/aws/aws-app-mesh-controller-for-k8s/tree/master/config/helm/appmesh-controller#without-irsa)

## 8. ***You need to add two labels to the api namespace: ```mesh``` and ```appmesh.k8s.aws/sidecarInjectorWebhook```. These labels instruct the controller to inject and configure the Envoy proxies in the pods.***
```bash
kubectl label namespace $APP_NS mesh=$APP_NS
kubectl label namespace $APP_NS appmesh.k8s.aws/sidecarInjectorWebhook=enabled
```

## 9. Create Mesh
```bash
 kubectl apply -f api-mesh.yaml 
```

## 10. Add service account to deployment spec.
```bash
***
   spec:
      serviceAccountName: envoy-proxy
      containers:
***

# ERROR 
# StreamAggregatedResources gRPC config stream to appmesh-envoy-management.us-east-1.amazonaws.com:443 closed: 7, Unauthorized to perform appmesh:StreamAggregatedResources for arn:aws:appmesh:us-east-1:<AWS_ACCOUNT_ID>:mesh/api/virtualNode/index-backend-node.
```
## 11. Create mesh objects and deploy apps
```bash
kubectl apply -f pgmoviedb-appmesh.yaml
kubectl apply -f pgmoviedb-deployment.yaml

kubectl apply -f nodeapi-appmesh.yaml
kubectl apply -f nodeapi-deployment.yaml

kubectl apply -f index-backend-appmesh.yaml
kubectl apply -f  index-backend-deployment.yaml

kubectl apply -f index-appmesh.yaml
kubectl apply -f index-deployment.yaml

kubectl apply -f frontend-appmesh.yaml
kubectl apply -f frontend-deployment.yaml
```

### 12.1 Deploy virtual gateway (Option 1) (BEST OPTION TO LEARN)
```bash
kubectl label namespace $APP_NS gateway=ingress-gw

VGW=frontend NS=api envsubst <  virtual-gateway-01.yaml | kubectl apply -f -
```

### Deploy virtual gateway (Option 2)
#### Create a namespace with injection enabled:
```bash
helm upgrade -i appmesh-gateway eks/appmesh-gateway \
    --namespace api \
    --set serviceAccount.name=envoy-proxy \
    --set serviceAccount.create=false  \
    --set log.level=debug
```
### 12.2 Deploy alb ingress
```bash
# Requires aws load balancer controller installed
CERT_ARN=*** envsubst < alb-ingress.yaml | kubectl apply -f -
```

# 13. X-Ray

### 13.1
```bash
export XRAY_POLICY=001_xray-policy
cat <<EOF> $XRAY_POLICY.json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "xray:GetSamplingStatisticSummaries",
                "xray:PutTelemetryRecords",
                "xray:GetSamplingRules",
                "xray:GetSamplingTargets",
                "xray:PutTraceSegments"
            ],
            "Resource": "*"
        }
    ]
}
EOF
```

### 13.2 Create an X-Ray IAM policy
```bash
XRAY_POLICY_ARN=$(aws iam create-policy \
    --policy-name ${XRAY_POLICY} \
    --policy-document file://${XRAY_POLICY}.json --query Policy.Arn --output text)
```
#### 13.3 Attach policy to role
```bash
aws iam attach-role-policy --policy-arn arn:aws:iam::$AWS_ACCOUNT_ID:policy/$XRAY_POLICY --role-name $ENVOY_IAM

```
```bash
helm upgrade -i appmesh-controller eks/appmesh-controller \
    --namespace appmesh-system \
    --set region=$AWS_REGION \
    --set serviceAccount.create=false \
    --set serviceAccount.name=appmesh-controller \
    --set image.tag=v1.10.0-linux_arm64 \
    --set tracing.enabled=true \
    --set tracing.provider=x-ray \
    --set log.level=debug
```

### Issues:
>##### Error
> kubectl describe rs pgmoviedb-746c6f7d8b:
> Warning  FailedCreate  2m7s (x17 over 7m35s)  replicaset-controller  Error creating: admission webhook "mpod.appmesh.k8s.aws" denied the request: sidecarInject enabled but no matching VirtualNode or VirtualGateway found
>###### Solution:
> Create mesh objects
> kubectl apply -f pgmoviedb-appmesh.yaml
> ##### Error
> Namespace stuck on terminating status
> ###### Solution
> Remove the finalizers array block from the spec section https://aws.amazon.com/premiumsupport/knowledge-center/eks-terminated-namespaces/
> ##### Error
> python-alpine image python:3.7.3-alpine3.9 unable to resolve 
> ```nslookup: can't resolve '(null)': Name does not resolve```
> > ###### Solution
> Upgraded to python:alpine3.16
>  ###### Reference:
> - https://github.com/gliderlabs/docker-alpine/issues/476
> ##### Error
> Error from server (failed to find matching virtualGateway for gatewayRoute: gateway-route-default, expecting 1 but found 0): error when creating "virtual-gateway-01.yaml": admission webhook "mgatewayroute.appmesh.k8s.aws" denied the request: failed to find matching virtualGateway for gatewayRoute: gateway-route-default, expecting 1 but found 0
> ###### Solution
> kubectl label namespace $APP_NS gateway=ingress-gw
> ##### Error
> 2023-04-27T21:54:22Z [Error] Sending segment batch failed with: AccessDeniedException: status code: 403, request id: 978bf844-fe96-4a8d-9e28-e3ac46c29aa4
> ###### Solution
> Attach PutTraceSegments to pod service account or node role.

# Extras
###  Tag all subnets in a given VPC with the specified key-value pair:
```bash
subnet_ids=($(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC" --query "Subnets[*].SubnetId" --output text))

for subnet_id in "${subnet_ids[@]}"
do
    aws ec2 create-tags --resources "$subnet_id" --tags Key=kubernetes.io/cluster/"$CLUSTER_NAME",Value=shared
done
```
### Retrieve all public subnets with the tag aws-cdk:subnet-type=Public, save them in an array, and tag them with the specified key-value pair:
```bash
public_subnet_ids=($(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC" "Name=tag:aws-cdk:subnet-type,Values=Public" --query "Subnets[*].SubnetId" --output text))

for public_subnet_id in "${subnet_ids[@]}"
do
    aws ec2 create-tags --resources "$public_subnet_id" --tags Key=kubernetes.io/role/elb,Value=1
done
```
#### Retrieve all private subnets with the tag aws-cdk:subnet-type=Private, save them in an array, and tag them with the specified key-value pair:
```bash
private_subnet_ids=($(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC" "Name=tag:aws-cdk:subnet-type,Values=Private" --query "Subnets[*].SubnetId" --output text))

for private_subnet_id in "${subnet_ids[@]}"
do
    aws ec2 create-tags --resources "$private_subnet_id" --tags Key=kubernetes.io/role/internal-elb,Value=1
done
```
# ArgoCD
```bash
kubectl apply -f other/api-namespace.yaml
# Create pod service account ENVOY_PROXY
# Create storage class efs-sc-dynamic
# PATH EKS/AppMesh
```


# Reference
- [AWS AppMesh Coltroller WIKI](https://aws.github.io/aws-app-mesh-controller-for-k8s/)
- [App Mesh Controller](https://github.com/aws/aws-app-mesh-controller-for-k8s/tree/master/config/helm/appmesh-controller)
- [Getting started with AWS App Mesh and Amazon EKS](https://aws.amazon.com/blogs/containers/getting-started-with-app-mesh-and-eks/)
- [Cross Amazon EKS cluster App Mesh using AWS Cloud Map](https://aws.amazon.com/blogs/containers/cross-amazon-eks-cluster-app-mesh-using-aws-cloud-map/)
- [EKS Helm Charts](https://github.com/aws/eks-charts/tree/master/stable/aws-for-fluent-bit)
- API DESIGN https://aws.github.io/aws-app-mesh-controller-for-k8s/reference/api_design/
- Manifest Template v1beta2 https://github.com/aws/aws-app-mesh-examples/blob/main/walkthroughs/howto-k8s-alb/v1beta2/manifest.yaml.template