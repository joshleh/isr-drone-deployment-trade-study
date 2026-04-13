PYTHON ?= python3
MPLCONFIGDIR ?= /tmp/mpl
DEMO_PORT ?= 8010

.PHONY: install test demo policy sweep export live-demo serve-demo

install:
	$(PYTHON) -m pip install -e .

test:
	PYTHONPATH=src $(PYTHON) -m unittest discover -s tests -v

demo:
	MPLCONFIGDIR=$(MPLCONFIGDIR) $(PYTHON) scripts/run_demo.py

policy:
	MPLCONFIGDIR=$(MPLCONFIGDIR) $(PYTHON) scripts/run_policy_comparison.py

sweep:
	MPLCONFIGDIR=$(MPLCONFIGDIR) $(PYTHON) scripts/run_sweep.py --config configs/sweeps/sweep_01.yaml

export:
	MPLCONFIGDIR=$(MPLCONFIGDIR) $(PYTHON) scripts/export_results.py

live-demo:
	$(PYTHON) scripts/build_live_demo.py

serve-demo:
	$(PYTHON) -m http.server $(DEMO_PORT) --bind 127.0.0.1
