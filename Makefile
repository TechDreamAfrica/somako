# Makefile for running tests and development tasks

# Default target
.PHONY: help
help:
	@echo "Available commands:"
	@echo "  test          - Run all tests"
	@echo "  test-unit     - Run only unit tests"
	@echo "  test-integration - Run only integration tests"
	@echo "  test-pwa      - Run only PWA tests"
	@echo "  test-coverage - Run tests with coverage report"
	@echo "  test-verbose  - Run tests with verbose output"
	@echo "  test-fast     - Run tests without migrations"
	@echo "  lint          - Run code linting"
	@echo "  clean         - Clean test artifacts"

# Test commands
.PHONY: test
test:
	python manage.py test food food_pwa --verbosity=2

.PHONY: test-unit
test-unit:
	python manage.py test food.test_models food.test_forms food.test_utils --verbosity=2

.PHONY: test-integration
test-integration:
	python manage.py test food.test_integration --verbosity=2

.PHONY: test-pwa
test-pwa:
	python manage.py test food_pwa.test_views --verbosity=2

.PHONY: test-coverage
test-coverage:
	coverage run --source='.' manage.py test food food_pwa
	coverage report -m
	coverage html

.PHONY: test-verbose
test-verbose:
	python manage.py test food food_pwa --verbosity=3 --debug-mode

.PHONY: test-fast
test-fast:
	python manage.py test food food_pwa --keepdb --parallel

.PHONY: test-specific
test-specific:
	@echo "Usage: make test-specific TEST=food.test_models.RestaurantModelTest.test_create_restaurant"
	python manage.py test $(TEST) --verbosity=2

# Development commands
.PHONY: runserver
runserver:
	python manage.py runserver

.PHONY: migrate
migrate:
	python manage.py migrate

.PHONY: makemigrations
makemigrations:
	python manage.py makemigrations

.PHONY: shell
shell:
	python manage.py shell

.PHONY: createsuperuser
createsuperuser:
	python manage.py createsuperuser

# Code quality commands
.PHONY: lint
lint:
	flake8 food/ food_pwa/ --max-line-length=120
	pylint food/ food_pwa/

.PHONY: format
format:
	black food/ food_pwa/
	isort food/ food_pwa/

# Cleanup commands
.PHONY: clean
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -name "*.pyc" -delete
	find . -name "*.pyo" -delete
	find . -name ".coverage" -delete
	rm -rf htmlcov/
	rm -rf .pytest_cache/

.PHONY: clean-migrations
clean-migrations:
	find . -path "*/migrations/*.py" -not -name "__init__.py" -delete
	find . -path "*/migrations/*.pyc" -delete

# Database commands  
.PHONY: reset-db
reset-db:
	rm -f db.sqlite3
	python manage.py migrate
	python manage.py createsuperuser --noinput --username admin --email admin@example.com || true

.PHONY: load-fixtures
load-fixtures:
	python manage.py loaddata food/fixtures/categories.json
	python manage.py loaddata food/fixtures/sample_restaurants.json

# Docker commands (if using Docker)
.PHONY: docker-test
docker-test:
	docker-compose -f docker-compose.test.yml up --build --abort-on-container-exit

.PHONY: docker-clean
docker-clean:
	docker-compose -f docker-compose.test.yml down -v
