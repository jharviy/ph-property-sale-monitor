.PHONY: install run etl analyze schedule test test-cov lint fmt clean

install:
	pip install -r requirements.txt

# Full pipeline: ETL + analysis for today
run:
	python main.py

# ETL only (no analysis)
etl:
	python main.py --mode etl

# Analysis on existing data
analyze:
	python main.py --mode analyze

# Start the daily scheduler
schedule:
	python scheduler.py

# Run scheduler immediately once (useful for testing)
schedule-now:
	python scheduler.py --now

# Tests
test:
	pytest tests/ -v

test-cov:
	pytest tests/ -v --cov=src --cov-report=term-missing --cov-report=html

# Code quality
lint:
	python -m isort --check-only src/ tests/
	python -m black --check src/ tests/

fmt:
	python -m isort src/ tests/
	python -m black src/ tests/

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -name "*.pyc" -delete
	rm -rf .pytest_cache htmlcov .coverage
