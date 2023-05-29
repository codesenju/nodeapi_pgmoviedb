# Setup Guide

### Prerequisite:
- docker
- docker-compsoe
- Internet access from where you will be building the image in order to download [IMDb datasets](https://www.imdb.com/interfaces/).
- jq

### Quick Setup:
```shell
docker-compose up -d
```
### Test API

```shell
curl localhost:3000/api/v1/movies | jq 
```

## Visit http://localhost:8080