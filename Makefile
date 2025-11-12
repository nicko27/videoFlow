# VideoFlow Makefile
# Simplifies common development tasks

.PHONY: help install install-dev clean test test-cov lint format type-check security docs run build

# Default target
.DEFAULT_GOAL := help

# Python interpreter
PYTHON := python3

# Project directories
SRC_DIR := src
TEST_DIR := tests
DOCS_DIR := docs

help: ## Show this help message
	@echo "VideoFlow - Available Commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""

install: ## Install project dependencies
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r requirements.txt

install-dev: install ## Install development dependencies
	$(PYTHON) -m pip install -r requirements-dev.txt
	pre-commit install

clean: ## Remove build artifacts and cache files
	@echo "Cleaning build artifacts..."
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*~" -delete
	@echo "Clean complete!"

test: ## Run tests
	pytest $(TEST_DIR) -v

test-cov: ## Run tests with coverage report
	pytest $(TEST_DIR) --cov=$(SRC_DIR) --cov-report=html --cov-report=term

test-fast: ## Run tests without coverage (faster)
	pytest $(TEST_DIR) -v --no-cov

test-watch: ## Run tests in watch mode
	pytest-watch $(TEST_DIR) -v

lint: ## Run linting checks
	@echo "Running flake8..."
	flake8 $(SRC_DIR) $(TEST_DIR) --max-line-length=100 --statistics
	@echo "Running pylint..."
	pylint $(SRC_DIR) --max-line-length=100 --disable=C0103,R0913,R0914 || true

format: ## Format code with black and isort
	@echo "Formatting with black..."
	black $(SRC_DIR) $(TEST_DIR) --line-length=100
	@echo "Sorting imports with isort..."
	isort $(SRC_DIR) $(TEST_DIR) --profile black --line-length=100

format-check: ## Check if code is properly formatted
	black $(SRC_DIR) $(TEST_DIR) --check --line-length=100
	isort $(SRC_DIR) $(TEST_DIR) --check --profile black --line-length=100

type-check: ## Run type checking with mypy
	mypy $(SRC_DIR) --ignore-missing-imports

security: ## Run security checks
	@echo "Running bandit security scan..."
	bandit -r $(SRC_DIR) -f json -o bandit-report.json || true
	bandit -r $(SRC_DIR)
	@echo "Checking dependencies for vulnerabilities..."
	safety check || true

security-report: ## Generate security report
	bandit -r $(SRC_DIR) -f html -o security-report.html
	@echo "Security report generated: security-report.html"

docstrings: ## Check docstring coverage
	$(PYTHON) check_docstrings.py

pre-commit: ## Run pre-commit hooks on all files
	pre-commit run --all-files

quality: format lint type-check security ## Run all quality checks

run: ## Run the application
	$(PYTHON) main.py

build: clean ## Build distribution packages
	$(PYTHON) setup.py sdist bdist_wheel

build-app: ## Build macOS application
	chmod +x build_app.sh
	./build_app.sh

install-local: ## Install package locally in development mode
	$(PYTHON) -m pip install -e .

uninstall: ## Uninstall package
	$(PYTHON) -m pip uninstall videoflow -y

translate: ## Run translation scripts
	$(PYTHON) translate_to_english.py
	$(PYTHON) translate_docstrings.py

stats: ## Show project statistics
	@echo "=== VideoFlow Project Statistics ==="
	@echo ""
	@echo "Python files:"
	@find $(SRC_DIR) -name "*.py" | wc -l
	@echo ""
	@echo "Lines of code:"
	@find $(SRC_DIR) -name "*.py" -exec wc -l {} + | tail -1
	@echo ""
	@echo "Test files:"
	@find $(TEST_DIR) -name "*.py" | wc -l
	@echo ""
	@echo "Test coverage:"
	@pytest $(TEST_DIR) --cov=$(SRC_DIR) --cov-report=term-missing | grep TOTAL || echo "Run 'make test-cov' first"
	@echo ""
	@echo "Docstring coverage:"
	@$(PYTHON) check_docstrings.py | grep "Overall Coverage" || echo "Run 'make docstrings' for details"

todo: ## Show TODO comments in code
	@echo "=== TODO items in codebase ==="
	@grep -rn "TODO\|FIXME\|XXX\|HACK" $(SRC_DIR) --color=auto || echo "No TODO items found!"

deps-update: ## Update dependencies to latest versions
	$(PYTHON) -m pip list --outdated
	@echo ""
	@echo "Run 'pip install --upgrade <package>' to update specific packages"

deps-tree: ## Show dependency tree
	pipdeptree

ci-local: quality test ## Run CI checks locally
	@echo ""
	@echo "✅ All CI checks passed!"

release-check: ## Check if ready for release
	@echo "=== Release Readiness Checklist ==="
	@echo ""
	@echo "Running quality checks..."
	@make quality
	@echo ""
	@echo "Running tests..."
	@make test-cov
	@echo ""
	@echo "Checking docstrings..."
	@make docstrings
	@echo ""
	@echo "Security scan..."
	@make security
	@echo ""
	@echo "✅ Release checks complete!"

.PHONY: venv
venv: ## Create virtual environment
	$(PYTHON) -m venv venv
	@echo ""
	@echo "Virtual environment created!"
	@echo "Activate with: source venv/bin/activate"

init: venv install-dev ## Initialize development environment
	@echo ""
	@echo "✅ Development environment initialized!"
	@echo "Run 'source venv/bin/activate' to activate the virtual environment"
