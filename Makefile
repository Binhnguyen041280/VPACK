# ============================================
# ePACK - Makefile for Common Operations
# ============================================
# This Makefile provides convenient commands for
# building, running, and managing ePACK.
#
# Usage:
#   make help           Show available commands
#   make install        Install all dependencies
#   make build          Build frontend and backend
#   make start-dev      Start development servers
#   make docker-build   Build Docker images
#   make docker-up      Start Docker containers
#   make clean          Clean build artifacts
#   make test           Run tests (when available)

.PHONY: help install build start-dev start-frontend start-backend docker-build docker-up docker-down clean test lint format

# ============================================
# CONFIGURATION
# ============================================

# Python command (try python3 first, fallback to python)
PYTHON := $(shell command -v python3 2> /dev/null || command -v python 2> /dev/null)

# Node/npm commands
NODE := $(shell command -v node 2> /dev/null)
NPM := $(shell command -v npm 2> /dev/null)

# Project directories
FRONTEND_DIR := frontend
BACKEND_DIR := backend
SCRIPTS_DIR := scripts

# Colors for output
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[1;33m
BLUE := \033[0;34m
NC := \033[0m # No Color

# ============================================
# HELP
# ============================================

help: ## Show this help message
	@echo "$(BLUE)╔════════════════════════════════════════════════════════════╗$(NC)"
	@echo "$(BLUE)║$(NC)  ePACK - Makefile Commands"
	@echo "$(BLUE)╚════════════════════════════════════════════════════════════╝$(NC)"
	@echo ""
	@echo "$(GREEN)Available targets:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(BLUE)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(YELLOW)Examples:$(NC)"
	@echo "  make install          # Install all dependencies"
	@echo "  make build            # Build all components"
	@echo "  make start-dev        # Start development servers"
	@echo "  make docker-up        # Start with Docker"
	@echo ""

# ============================================
# INSTALLATION
# ============================================

install: install-frontend install-backend ## Install all dependencies

install-frontend: ## Install frontend dependencies
	@echo "$(BLUE)[i]$(NC) Installing frontend dependencies..."
	@cd $(FRONTEND_DIR) && $(NPM) ci
	@echo "$(GREEN)[✓]$(NC) Frontend dependencies installed"

install-backend: ## Install backend dependencies
	@echo "$(BLUE)[i]$(NC) Installing backend dependencies..."
	@cd $(BACKEND_DIR) && $(PYTHON) -m pip install --upgrade pip -q
	@cd $(BACKEND_DIR) && $(PYTHON) -m pip install -r requirements.txt -q
	@echo "$(GREEN)[✓]$(NC) Backend dependencies installed"

install-dev: install ## Install development dependencies
	@echo "$(BLUE)[i]$(NC) Installing development dependencies..."
	@cd $(FRONTEND_DIR) && $(NPM) install --save-dev eslint prettier
	@cd $(BACKEND_DIR) && $(PYTHON) -m pip install black flake8 pytest -q
	@echo "$(GREEN)[✓]$(NC) Development dependencies installed"

# ============================================
# BUILD
# ============================================

build: ## Build all components
	@echo "$(BLUE)╔════════════════════════════════════════════════════════════╗$(NC)"
	@echo "$(BLUE)║$(NC)  Building ePACK"
	@echo "$(BLUE)╚════════════════════════════════════════════════════════════╝$(NC)"
	@bash $(SCRIPTS_DIR)/build_all.sh

build-frontend: ## Build frontend only
	@echo "$(BLUE)[i]$(NC) Building frontend..."
	@cd $(FRONTEND_DIR) && $(NPM) run build
	@echo "$(GREEN)[✓]$(NC) Frontend built successfully"

build-backend: ## Set up backend only
	@echo "$(BLUE)[i]$(NC) Setting up backend..."
	@cd $(BACKEND_DIR) && $(PYTHON) -m pip install -r requirements.txt -q
	@cd $(BACKEND_DIR) && $(PYTHON) database.py
	@echo "$(GREEN)[✓]$(NC) Backend set up successfully"

build-production: ## Build for production
	@bash $(SCRIPTS_DIR)/build_all.sh --production

build-clean: ## Clean build and rebuild
	@bash $(SCRIPTS_DIR)/build_all.sh --clean

# ============================================
# DEVELOPMENT
# ============================================

start-dev: ## Start development servers (parallel)
	@echo "$(BLUE)[i]$(NC) Starting development servers..."
	@echo "$(YELLOW)[!]$(NC) Press Ctrl+C to stop both servers"
	@$(MAKE) -j2 start-frontend-dev start-backend-dev

start-frontend-dev: ## Start frontend development server
	@echo "$(GREEN)[✓]$(NC) Starting frontend on http://localhost:3000"
	@cd $(FRONTEND_DIR) && $(NPM) run dev

start-backend-dev: ## Start backend development server
	@echo "$(GREEN)[✓]$(NC) Starting backend on http://localhost:8080"
	@cd $(BACKEND_DIR) && $(PYTHON) app.py

start-frontend: ## Start frontend production server
	@echo "$(GREEN)[✓]$(NC) Starting frontend production server..."
	@cd $(FRONTEND_DIR) && $(NPM) run start

start-backend: ## Start backend production server
	@echo "$(GREEN)[✓]$(NC) Starting backend production server..."
	@cd $(BACKEND_DIR) && $(PYTHON) app.py

# ============================================
# DOCKER
# ============================================

docker-build: ## Build Docker images
	@echo "$(BLUE)[i]$(NC) Building Docker images..."
	@docker-compose build
	@echo "$(GREEN)[✓]$(NC) Docker images built successfully"

docker-up: ## Start Docker containers
	@echo "$(BLUE)[i]$(NC) Starting Docker containers..."
	@docker-compose up -d
	@echo "$(GREEN)[✓]$(NC) Docker containers started"
	@echo "$(BLUE)[i]$(NC) Frontend: http://localhost:3000"
	@echo "$(BLUE)[i]$(NC) Backend:  http://localhost:8080"

docker-up-build: ## Build and start Docker containers
	@echo "$(BLUE)[i]$(NC) Building and starting Docker containers..."
	@docker-compose up -d --build
	@echo "$(GREEN)[✓]$(NC) Docker containers running"

docker-down: ## Stop Docker containers
	@echo "$(BLUE)[i]$(NC) Stopping Docker containers..."
	@docker-compose down
	@echo "$(GREEN)[✓]$(NC) Docker containers stopped"

docker-logs: ## Show Docker container logs
	@docker-compose logs -f

docker-restart: docker-down docker-up ## Restart Docker containers

docker-clean: ## Remove Docker images and volumes
	@echo "$(YELLOW)[!]$(NC) Removing Docker images and volumes..."
	@docker-compose down -v --rmi all
	@echo "$(GREEN)[✓]$(NC) Docker cleaned"

# ============================================
# DATABASE
# ============================================

init-db: ## Initialize database
	@echo "$(BLUE)[i]$(NC) Initializing database..."
	@cd $(BACKEND_DIR) && $(PYTHON) database.py
	@echo "$(GREEN)[✓]$(NC) Database initialized"

reset-db: ## Reset database (WARNING: Deletes all data)
	@echo "$(RED)[!]$(NC) WARNING: This will delete all data!"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		rm -f $(BACKEND_DIR)/VTrack_db.db; \
		$(MAKE) init-db; \
	else \
		echo "$(YELLOW)[!]$(NC) Cancelled"; \
	fi

backup-db: ## Backup database
	@echo "$(BLUE)[i]$(NC) Backing up database..."
	@mkdir -p backups
	@cp $(BACKEND_DIR)/VTrack_db.db backups/VTrack_db_$(shell date +%Y%m%d_%H%M%S).db
	@echo "$(GREEN)[✓]$(NC) Database backed up to backups/"

# ============================================
# TESTING
# ============================================

test: ## Run all tests
	@echo "$(BLUE)[i]$(NC) Running tests..."
	@echo "$(YELLOW)[!]$(NC) Test suite not yet implemented"
	# @cd $(FRONTEND_DIR) && $(NPM) run test
	# @cd $(BACKEND_DIR) && $(PYTHON) -m pytest

test-frontend: ## Run frontend tests
	@echo "$(BLUE)[i]$(NC) Running frontend tests..."
	@cd $(FRONTEND_DIR) && $(NPM) run test

test-backend: ## Run backend tests
	@echo "$(BLUE)[i]$(NC) Running backend tests..."
	@cd $(BACKEND_DIR) && $(PYTHON) -m pytest

# ============================================
# CODE QUALITY
# ============================================

lint: lint-frontend lint-backend ## Run linters

lint-frontend: ## Lint frontend code
	@echo "$(BLUE)[i]$(NC) Linting frontend..."
	@cd $(FRONTEND_DIR) && $(NPM) run lint

lint-backend: ## Lint backend code
	@echo "$(BLUE)[i]$(NC) Linting backend..."
	@cd $(BACKEND_DIR) && $(PYTHON) -m flake8 .

format: format-frontend format-backend ## Format code

format-frontend: ## Format frontend code
	@echo "$(BLUE)[i]$(NC) Formatting frontend..."
	@cd $(FRONTEND_DIR) && npx prettier --write .

format-backend: ## Format backend code
	@echo "$(BLUE)[i]$(NC) Formatting backend..."
	@cd $(BACKEND_DIR) && $(PYTHON) -m black .

# ============================================
# CLEANUP
# ============================================

clean: ## Clean build artifacts
	@echo "$(BLUE)[i]$(NC) Cleaning build artifacts..."
	@rm -rf $(FRONTEND_DIR)/.next
	@rm -rf $(FRONTEND_DIR)/out
	@find $(BACKEND_DIR) -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find $(BACKEND_DIR) -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "$(GREEN)[✓]$(NC) Build artifacts cleaned"

clean-all: clean ## Clean everything including dependencies
	@echo "$(RED)[!]$(NC) Removing all dependencies..."
	@rm -rf $(FRONTEND_DIR)/node_modules
	@rm -rf $(BACKEND_DIR)/venv
	@echo "$(GREEN)[✓]$(NC) Everything cleaned"

clean-logs: ## Clean log files
	@echo "$(BLUE)[i]$(NC) Cleaning log files..."
	@rm -rf $(BACKEND_DIR)/var/logs/*
	@echo "$(GREEN)[✓]$(NC) Logs cleaned"

# ============================================
# UTILITIES
# ============================================

check-deps: ## Check if required dependencies are installed
	@echo "$(BLUE)[i]$(NC) Checking dependencies..."
	@command -v $(NODE) >/dev/null 2>&1 || { echo "$(RED)[✗]$(NC) Node.js not found"; exit 1; }
	@command -v $(NPM) >/dev/null 2>&1 || { echo "$(RED)[✗]$(NC) npm not found"; exit 1; }
	@command -v $(PYTHON) >/dev/null 2>&1 || { echo "$(RED)[✗]$(NC) Python not found"; exit 1; }
	@command -v docker >/dev/null 2>&1 || echo "$(YELLOW)[!]$(NC) Docker not found (optional)"
	@echo "$(GREEN)[✓]$(NC) All required dependencies found"
	@echo "  Node: $$($(NODE) --version)"
	@echo "  npm:  $$($(NPM) --version)"
	@echo "  Python: $$($(PYTHON) --version)"

env-setup: ## Set up environment files from examples
	@echo "$(BLUE)[i]$(NC) Setting up environment files..."
	@[ ! -f .env ] && cp .env.example .env && echo "$(GREEN)[✓]$(NC) Created .env" || echo "$(YELLOW)[!]$(NC) .env already exists"
	@[ ! -f $(FRONTEND_DIR)/.env.local ] && cp $(FRONTEND_DIR)/.env.example $(FRONTEND_DIR)/.env.local && echo "$(GREEN)[✓]$(NC) Created frontend/.env.local" || echo "$(YELLOW)[!]$(NC) frontend/.env.local already exists"
	@[ ! -f $(BACKEND_DIR)/.env ] && cp $(BACKEND_DIR)/.env.example $(BACKEND_DIR)/.env && echo "$(GREEN)[✓]$(NC) Created backend/.env" || echo "$(YELLOW)[!]$(NC) backend/.env already exists"
	@echo "$(BLUE)[i]$(NC) Please edit the .env files and configure your settings"

status: ## Show project status
	@echo "$(BLUE)╔════════════════════════════════════════════════════════════╗$(NC)"
	@echo "$(BLUE)║$(NC)  ePACK Status"
	@echo "$(BLUE)╚════════════════════════════════════════════════════════════╝$(NC)"
	@echo ""
	@echo "$(BLUE)Dependencies:$(NC)"
	@command -v $(NODE) >/dev/null 2>&1 && echo "  $(GREEN)[✓]$(NC) Node: $$($(NODE) --version)" || echo "  $(RED)[✗]$(NC) Node not found"
	@command -v $(NPM) >/dev/null 2>&1 && echo "  $(GREEN)[✓]$(NC) npm: $$($(NPM) --version)" || echo "  $(RED)[✗]$(NC) npm not found"
	@command -v $(PYTHON) >/dev/null 2>&1 && echo "  $(GREEN)[✓]$(NC) Python: $$($(PYTHON) --version)" || echo "  $(RED)[✗]$(NC) Python not found"
	@command -v docker >/dev/null 2>&1 && echo "  $(GREEN)[✓]$(NC) Docker: $$(docker --version)" || echo "  $(YELLOW)[!]$(NC) Docker not found"
	@echo ""
	@echo "$(BLUE)Build Status:$(NC)"
	@[ -d $(FRONTEND_DIR)/.next ] && echo "  $(GREEN)[✓]$(NC) Frontend built" || echo "  $(YELLOW)[!]$(NC) Frontend not built"
	@[ -d $(FRONTEND_DIR)/node_modules ] && echo "  $(GREEN)[✓]$(NC) Frontend dependencies installed" || echo "  $(RED)[✗]$(NC) Frontend dependencies not installed"
	@[ -f $(BACKEND_DIR)/VTrack_db.db ] && echo "  $(GREEN)[✓]$(NC) Database initialized" || echo "  $(YELLOW)[!]$(NC) Database not initialized"
	@echo ""

# ============================================
# DEFAULT TARGET
# ============================================

.DEFAULT_GOAL := help
