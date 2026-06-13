.PHONY: install run etl analyze

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