#!/bin/bash
source .venv/bin/activate

cd security_group/
echo "Deploy security groups..."
cdk deploy --require-approval never

cd ../pgmoviedb/
echo "Deploy pgmoviedb..."
cdk deploy --require-approval never

cd ../nodeapi/
echo "Deploy nodeapi..."
cdk deploy --require-approval never

cd ../index/
echo "Deploy index.."
cdk deploy --require-approval never

cd ../frontend/
echo "Deploy frontend.."
cdk deploy --require-approval never

echo "Deployment complete!"