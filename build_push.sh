#!/bin/bash

cd postgres
docker buildx build --push --platform linux/arm64/v8,linux/amd64 --tag codesenju/pgmoviedb.api.local:latest .

cd ../nodeapi
docker buildx build --push --platform linux/arm64/v8,linux/amd64 --tag codesenju/nodeapi.api.local:latest .

cd ../index.api.local
docker buildx build --push --platform linux/arm64/v8,linux/amd64 --tag codesenju/index.api.local:v1 .

cd ../indexv2.api.local
docker buildx build --push --platform linux/arm64/v8,linux/amd64 --tag codesenju/index.api.local:v2 .

cd ../indexv3.api.local
docker buildx build --push --platform linux/arm64/v8,linux/amd64 --tag codesenju/index.api.local:v3 .

cd ../frontend.api.local
docker buildx build --push --platform linux/arm64/v8,linux/amd64 --tag codesenju/frontend.api.local:latest .

cd ../index-backend.api.local
docker buildx build --push --platform linux/arm64/v8,linux/amd64 --tag codesenju/index-backend.api.local:latest .