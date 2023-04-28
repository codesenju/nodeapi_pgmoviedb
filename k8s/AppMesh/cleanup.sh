#!/bin/zsh
kubectl delete -f virtual-gateway-01.yaml

kubectl delete -f frontend-deployment.yaml
kubectl delete -f frontend-appmesh.yaml

kubectl delete -f index-deployment.yaml
kubectl delete -f index-appmesh.yaml

kubectl delete -f index-backend-deployment.yaml
kubectl delete -f index-backend-appmesh.yaml

kubectl delete -f nodeapi-deployment.yaml
kubectl delete -f nodeapi-appmesh.yaml

kubectl delete -f pgmoviedb-deployment.yaml
kubectl delete -f pgmoviedb-appmesh.yaml