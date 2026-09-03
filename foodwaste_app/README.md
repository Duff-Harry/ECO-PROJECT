# Food Waste Treatment — Pareto Explorer

A free Streamlit dashboard over the results of the GAMSPy/BARON superstructure
optimization in `DetermineSceanrio1.ipynb`. It does **not** run any solver —
it reads pre-solved CSV files and lets you explore the cost/GHG/marine-
eutrophication tradeoff and the resulting technology blend per feedstock
scenario (Household, Restaurant, Institutional, Retail, Market).

## Why the app doesn't solve anything itself

The notebook solves a nonconvex mixed-integer nonlinear program with BARON
(a commercial global solver, via GAMS). Two things make that incompatible
with running live inside a free Streamlit Cloud app:

- **License:** GAMS's free Community license caps BARON specifically at
  300 variables / 300 equations / 100 nonlinear nonzeros — far below this
  model's size. It will not solve this model.
- **Runtime:** the notebook's own comments note the full 3-objective grid
  takes 6–25+ hours per feedstock scenario at a 900-second-per-point time
  limit. Streamlit Community Cloud gives a small shared-CPU container that
  sleeps on inactivity — it isn't built for multi-hour compute inside a page
  load, regardless of which solver you use.

So: solve once, offline, wherever you have BARON access (or, longer-term, a
free solver such as SCIP/Couenne via Pyomo, or NEOS Server's free hosted
BARON for a much smaller/faster problem) — then point this app at the
result. That keeps the deployed app instant and free.

## Project layout

```
app.py                       Streamlit app (5 tabs: explorer, blend,
                              compare, feedstock, raw data)
generate_sample_data.py      Generates the placeholder demo data in data/
data/
  pareto_all_scenarios.csv   One row per Pareto point per scenario
  scenario_comparison.csv    Cheapest blend, one row per scenario
  feedstock_composition.csv  The 5 feed characterizations
requirements.txt
.streamlit/config.toml       Theme
```

## Using your real solved data instead of the placeholder

Your notebook already writes files shaped exactly like what this app reads:

| App expects                       | Notebook produces (same columns)     |
|------------------------------------|---------------------------------------|
| `data/pareto_all_scenarios.csv`    | Cell 99: `pareto_all_scenarios.csv`   |
| `data/scenario_comparison.csv`     | Cell 85: `scenario_comparison.csv`    |
| `data/feedstock_composition.csv`   | Cell 83's 5 feed dicts — export these as one CSV, one row per scenario, same column names as HOUSEHOLD/RESTAURANT/etc. |

Just copy your real CSVs into `data/` with those exact filenames and column
names, then in `app.py` set `is_placeholder = False` near the top. No other
code changes needed — the app reads whatever is in `data/` at load time.

If you only have partial results (e.g. 2 of 5 scenarios solved), that's
fine — the app works with however many scenarios are present in the CSV.

## Running locally

```bash
pip install -r requirements.txt
python generate_sample_data.py   # only needed once, for placeholder data
streamlit run app.py
```

## Deploying to Streamlit Community Cloud (free)

1. Push this folder to a GitHub repo (public, or private on a plan that
   supports it).
2. Go to share.streamlit.io, connect the repo, set the main file to
   `app.py`, and deploy.
3. No secrets or API keys are needed — the app only reads the bundled CSVs.

## Extending later: on-demand re-solves

If you eventually want a user to enter a custom feed composition and get a
fresh answer, that's a separate, harder feature: it needs an actual solver
reachable from the app (e.g. NEOS Server's free hosted BARON, called
asynchronously — submit, then poll for a result) and a much smaller/faster
problem than the full 5-scenario, multi-hour grid this app currently
visualizes. Don't build that into this same request/response flow — treat
it as a background job with its own "submitted, check back" UI state.
