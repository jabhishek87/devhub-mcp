IMAGE := devhub-mcp
TAG := latest
COMPOSE := docker compose -f docker-compose.yml

.PHONY: help build run up down test test-docker healthz clean lint

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

build: ## Build Docker image
	docker build -t $(IMAGE):$(TAG) .

run: ## Run gateway container (stdio mode)
	docker run --rm -i \
		-e GERRIT_USER -e GERRIT_HTTP_PASSWORD \
		-e JENKINS_URL -e JENKINS_USER -e JENKINS_API_TOKEN \
		$(IMAGE):$(TAG)

up: ## docker compose up (detached)
	$(COMPOSE) up -d

down: ## docker compose down
	$(COMPOSE) down

test: ## Run tests locally (requires deps installed)
	python tests/test_tools.py

test-docker: build ## Run tests inside container
	docker run --rm $(IMAGE):$(TAG) python tests/test_tools.py

healthz: build ## Call healthz in container
	docker run --rm $(IMAGE):$(TAG) python -c "import asyncio,json;from main import hub_mcp;print(json.loads(asyncio.run(hub_mcp.call_tool('healthz',{})).content[0].text))"

lint: build ## Lint Python files in container
	docker run --rm $(IMAGE):$(TAG) python -m py_compile main.py
	docker run --rm $(IMAGE):$(TAG) python -m py_compile mcp_servers/gerrit.py
	docker run --rm $(IMAGE):$(TAG) python -m py_compile mcp_servers/jenkins.py
	docker run --rm $(IMAGE):$(TAG) python -m py_compile mcp_servers/middleware.py
	docker run --rm $(IMAGE):$(TAG) python -m py_compile mcp_servers/proxy.py
	@echo "All files OK"

clean: ## Remove image and containers
	$(COMPOSE) down --rmi local 2>/dev/null || true
	docker rmi $(IMAGE):$(TAG) 2>/dev/null || true
