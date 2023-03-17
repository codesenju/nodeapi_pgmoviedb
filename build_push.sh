#!/bin/bash
echo "Building images..."
docker-compose build
sleep 2
echo "Pushing images..."
docker push codesenju/pgmoviedb.api.local:latest
docker push codesenju/nodeapi.api.local:latest
docker push codesenju/index.api.local:v1
docker push codesenju/index.api.local:v2
docker push codesenju/index.api.local:v3
docker push codesenju/frontend.api.local:latest
docker push codesenju/index-backend.api.local:latest
echo "Done!"