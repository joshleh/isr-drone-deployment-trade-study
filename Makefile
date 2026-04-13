PYTHON ?= python3
MPLCONFIGDIR ?= /tmp/mpl

.PHONY: install test demo policy sweep export

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
