# One-command reproduce. Committed slim data is enough for everything except `data`.
PY ?= python

.PHONY: install test evals app monitor data video all

install:            ## app + eval dependencies
	$(PY) -m pip install -r requirements.txt pytest

test:               ## golden-path tests
	$(PY) -m pytest -q

evals:              ## re-run every evaluation into results/
	$(PY) eval/within_pitcher.py
	$(PY) eval/league_monitor.py
	$(PY) eval/robustness.py
	$(PY) eval/power.py

monitor:            ## ranked review list for the 2025 season, live baseline
	$(PY) -m pim data/slim/statcast_2025.parquet --mode live --top 25

app:                ## the Streamlit app on http://localhost:8501
	$(PY) -m streamlit run app.py

data:               ## re-pull Statcast 2023-25 from Baseball Savant (~50 min, polite rate) and rebuild slim files
	$(PY) -m pip install -r requirements-pipeline.txt
	$(PY) scripts/pull_statcast.py
	$(PY) scripts/make_slim.py 2023 2024 2025

video:              ## rebuild the demo video (see video/README.md)
	cd video/src && $(PY) voice.py && $(PY) prep.py && $(PY) music.py && $(PY) mix.py && $(PY) render.py all && $(PY) assemble.py

all: install test evals
