PYTHON ?= python
DEMO_PORT ?= 8010
LIVE_DEMO_URL ?= http://127.0.0.1:$(DEMO_PORT)/docs/live_demo/index.html

.PHONY: install test demo policy sweep export figures live-demo serve-demo all clean help

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

install: ## Install package in editable mode
	$(PYTHON) -m pip install -e .

test: ## Run the unit tests
	$(PYTHON) -m unittest discover -s tests -v

demo: ## Run the priority-weighted trade-study demo
	$(PYTHON) scripts/run_demo.py

policy: ## Run the dynamic policy comparison
	$(PYTHON) scripts/run_policy_comparison.py

sweep: ## Run the default sweep (configs/sweeps/sweep_01.yaml)
	$(PYTHON) scripts/run_sweep.py --config configs/sweeps/sweep_01.yaml

export: ## Export sweep figures to docs/figures/
	$(PYTHON) scripts/export_results.py

figures: demo policy ## Regenerate demo + policy figures and artifacts

live-demo: ## Build the live-demo HTML from the latest local artifacts
	$(PYTHON) scripts/build_live_demo.py
	@echo "Live demo: $(LIVE_DEMO_URL)"

serve-demo: ## Serve the repo over http (open the live demo in a browser)
	@echo "Serving on $(LIVE_DEMO_URL)"
	$(PYTHON) -m http.server $(DEMO_PORT) --bind 127.0.0.1

all: install test demo policy live-demo ## Full reproducible build (install + test + artifacts + site)

clean: ## Remove generated results, dashboards, and the rendered live demo
	rm -rf results
	rm -f docs/live_demo/index.html
