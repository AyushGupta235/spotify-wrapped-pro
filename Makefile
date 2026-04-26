SHELL := /bin/bash
PROJECT_DIR := $(shell pwd)
VENV_PYTHON := $(PROJECT_DIR)/.venv/bin/python
PLIST_SRC   := $(PROJECT_DIR)/scripts/collector.plist
PLIST_DEST  := $(HOME)/Library/LaunchAgents/com.spotify-wrapped.collector.plist

.PHONY: setup run ingest whoami collector-install collector-uninstall collector-logs

setup:
	python3 -m venv .venv
	.venv/bin/pip install -e .
	@if [ ! -f .env ]; then cp .env.example .env; echo "\nCreated .env — fill in your Spotify credentials before continuing.\n"; fi

run:
	.venv/bin/streamlit run app.py

ingest:
	$(VENV_PYTHON) -m scripts.ingest all

whoami:
	$(VENV_PYTHON) -m scripts.ingest whoami

# ── Background collector (runs every 6 hours via launchd) ──────────────────

collector-install:
	@echo "Installing 6-hour background collector..."
	@sed \
		-e "s|VENV_PYTHON|$(VENV_PYTHON)|g" \
		-e "s|PROJECT_DIR|$(PROJECT_DIR)|g" \
		$(PLIST_SRC) > $(PLIST_DEST)
	@launchctl load $(PLIST_DEST)
	@echo "Collector installed and started. Runs every 6 hours."
	@echo "Logs: /tmp/spotify-wrapped-collector.log"

collector-uninstall:
	@launchctl unload $(PLIST_DEST) 2>/dev/null || true
	@rm -f $(PLIST_DEST)
	@echo "Collector uninstalled."

collector-logs:
	@tail -f /tmp/spotify-wrapped-collector.log
