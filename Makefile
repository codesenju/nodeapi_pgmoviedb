# App and image names
COMPOSE_FILE=docker-compose.yml

# Docker build
.PHONY: build
build:
	docker compose --profile quick-setup -f $(COMPOSE_FILE) build

# Docker run (standalone)
.PHONY: run
run:
	docker compose --profile quick-setup -f $(COMPOSE_FILE) up --build

# Docker Compose up
.PHONY: up
up:
	docker compose --profile quick-setup -f $(COMPOSE_FILE) up -d

# Docker Compose down
.PHONY: down
down:
	docker compose --profile quick-setup -f $(COMPOSE_FILE) down

# Remove containers, volumes, and networks
.PHONY: clean
clean:
	docker compose --profile quick-setup -f $(COMPOSE_FILE) down -v --remove-orphans

# Shell into running FastAPI container
.PHONY: shell
shell:
	docker exec -it $$(docker ps -qf "name=fastapi") bash

# Tail logs from FastAPI container
.PHONY: logs
logs:
	docker compose --profile quick-setup -f $(COMPOSE_FILE) logs -f
