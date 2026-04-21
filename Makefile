.PHONY: setup run ingest whoami

setup:
	python3 -m venv .venv
	.venv/bin/pip install -e .
	@if [ ! -f .env ]; then cp .env.example .env; echo "\nCreated .env — fill in your Spotify credentials before continuing.\n"; fi

run:
	.venv/bin/streamlit run app.py

ingest:
	.venv/bin/python -m scripts.ingest all

whoami:
	.venv/bin/python -m scripts.ingest whoami
