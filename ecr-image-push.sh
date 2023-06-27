#!/bin/bash
docker-compose build
docker push 587878432697.dkr.ecr.us-east-1.amazonaws.com/pgmoviedb.api.local
docker push 587878432697.dkr.ecr.us-east-1.amazonaws.com/nodeapi.api.local
docker push 587878432697.dkr.ecr.us-east-1.amazonaws.com/index.api.local
docker push 587878432697.dkr.ecr.us-east-1.amazonaws.com/indexv2.api.local
docker push 587878432697.dkr.ecr.us-east-1.amazonaws.com/indexv3.api.local
docker push 587878432697.dkr.ecr.us-east-1.amazonaws.com/frontend.api.local
docker push 587878432697.dkr.ecr.us-east-1.amazonaws.com/index-backend.api.local