PYTHON ?= python

.PHONY: install test run clean

install:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -e .[dev]

test:
	pytest -q

clean:
	$(PYTHON) - <<'PY'
	from pathlib import Path
	import shutil
	for name in ("artifacts", "reports", ".pytest_cache", "htmlcov", "dist", "build"):
	    path = Path(name)
	    if path.exists():
	        shutil.rmtree(path)
	for egg in Path(".").glob("*.egg-info"):
	    shutil.rmtree(egg)
	PY
