#!/bin/bash
source .venv/bin/activate

cd frontend/
echo "Destroy frontend.."
printf y | cdk destroy --require-approval never

cd ../index/
echo "Destroy index.."
printf y |  cdk destroy --require-approval never

cd ../nodeapi/
echo "Destroy nodeapi..."
printf y |  cdk destroy --require-approval never

cd ../pgmoviedb/
echo "Destroy pgmoviedb..."
printf y |  cdk destroy --require-approval never

cd ../security_group/
echo "Destroy security groups..."
printf y |  cdk destroy --require-approval never

cd ../Ecs/
echo "Destroy ECS cluster..."
printf y |  cdk destroy --require-approval never

echo "Destruction complete!"