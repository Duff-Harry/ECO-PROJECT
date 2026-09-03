"""
Generates PLACEHOLDER/DEMO data shaped exactly like the outputs your GAMSPy
notebook (DetermineSceanrio1.ipynb) already produces:

  - pareto_all_scenarios.csv   <- same columns as your notebook's Cell 99 output
  - scenario_comparison.csv    <- same columns as your notebook's Cell 85 output
  - feedstock_composition.csv  <- the 5 HOUSEHOLD/RESTAURANT/... dicts from Cell 83
  - cost_breakdown.csv         <- each scenario's NAC split into Capital / Labor /
                                    Utilities / Overhead / Materials / Working
                                    capital (placeholder split -- see the notebook's
                                    costing cell for the real CCAC/CCLB/etc. terms)

This script exists ONLY so the app has something to render before you have a
real BARON solve finished. Once you have real output files with these exact
names and columns, just drop them into data/ and delete/ignore this script --
the app does not care whether the CSVs came from this generator or from BARON.

Run: python generate_sample_data.py
"""

import csv
import random

random.seed(42)

# ---------------------------------------------------------------------------
# The 5 feedstock characterizations, copied verbatim from notebook Cell 83
# ---------------------------------------------------------------------------
FEEDSTOCKS = {
    "Household": {
        "Moisture (%)": 72.52, "Volatile matter (%)": 82.39, "Ash (%)": 5.58,
        "Fixed carbon (%)": 12.03, "Carbohydrate (%)": 12.50, "Protein (%)": 13.53,
        "Lipid (%)": 10.60, "C (%)": 48.76, "H (%)": 6.29, "N (%)": 3.85,
        "O (%)": 40.69, "S (%)": 0.41, "HHV (MJ/kg)": 18.65,
    },
    "Restaurant": {
        "Moisture (%)": 75.70, "Volatile matter (%)": 81.72, "Ash (%)": 6.11,
        "Fixed carbon (%)": 12.17, "Carbohydrate (%)": 35.33, "Protein (%)": 21.39,
        "Lipid (%)": 25.00, "C (%)": 48.63, "H (%)": 6.50, "N (%)": 3.41,
        "O (%)": 41.17, "S (%)": 0.29, "HHV (MJ/kg)": 20.23,
    },
    "Institutional": {
        "Moisture (%)": 60.85, "Volatile matter (%)": 84.31, "Ash (%)": 5.01,
        "Fixed carbon (%)": 10.68, "Carbohydrate (%)": 42.11, "Protein (%)": 18.90,
        "Lipid (%)": 13.58, "C (%)": 46.72, "H (%)": 6.28, "N (%)": 3.70,
        "O (%)": 42.93, "S (%)": 0.37, "HHV (MJ/kg)": 22.69,
    },
    "Retail": {
        "Moisture (%)": 61.08, "Volatile matter (%)": 80.79, "Ash (%)": 7.73,
        "Fixed carbon (%)": 11.48, "Carbohydrate (%)": 11.57, "Protein (%)": 25.51,
        "Lipid (%)": 31.57, "C (%)": 50.09, "H (%)": 6.58, "N (%)": 4.09,
        "O (%)": 38.89, "S (%)": 0.35, "HHV (MJ/kg)": 24.74,
    },
    "Market": {
        "Moisture (%)": 89.18, "Volatile matter (%)": 75.14, "Ash (%)": 12.00,
        "Fixed carbon (%)": 12.86, "Carbohydrate (%)": 52.94, "Protein (%)": 12.37,
        "Lipid (%)": 3.00, "C (%)": 46.07, "H (%)": 5.70, "N (%)": 2.86,
        "O (%)": 44.91, "S (%)": 0.46, "HHV (MJ/kg)": 13.50,
    },
}

CONVERSION_ROUTES = ["HTL", "AND", "SLF", "CMP", "WWT", "INC"]

# Rough anchor economics per scenario (placeholder, loosely shaped by
# moisture/HHV so the demo isn't flat) -- NOT derived from the real model.
# nac in M$/yr, ghg in tCO2e/yr, ep in t N-eq/yr.
SCENARIO_ANCHORS = {
    #                nac_lo nac_hi  ghg_lo ghg_hi  ep_lo  ep_hi
    "Household":     (4.10,  7.80,  180,   950,    0.9,   4.2),
    "Restaurant":     (5.40,  9.60,  260,  1200,    1.4,   5.6),
    "Institutional": (6.10, 10.40,  310,  1350,    1.6,   6.1),
    "Retail":        (5.90, 11.20,  340,  1500,    1.8,   6.8),
    "Market":        (3.40,  6.90,  150,   820,    2.4,   7.9),
}

GRID_N = 3  # matches SCENARIO_GRID_N in the notebook


def blend_for(t, u):
    """Fake but smoothly-varying technology blend as a function of grid
    position (t = GHG-allowance level, u = EP-allowance level), both 0..1.
    Low t (tight GHG cap) leans on AND (biogas capture); high t leans on
    cheap/high-emission SLF+INC. Not physically derived -- just for a
    demo-able, visually coherent Pareto explorer."""
    and_pct = max(0.0, 55 * (1 - t) - 10 * u)
    wwt_pct = max(0.0, 20 * (1 - t) * (1 - u))
    slf_pct = max(0.0, 45 * t - 5 * (1 - u))
    inc_pct = max(0.0, 30 * t * u)
    cmp_pct = max(0.0, 15 * (1 - t) * u)
    htl_pct = max(0.0, 100 - (and_pct + wwt_pct + slf_pct + inc_pct + cmp_pct))
    raw = {"AND": and_pct, "WWT": wwt_pct, "SLF": slf_pct, "INC": inc_pct,
           "CMP": cmp_pct, "HTL": htl_pct}
    total = sum(raw.values()) or 1.0
    return {k: round(100 * v / total, 1) for k, v in raw.items()}


def format_blend(pct):
    parts = [f"{k} {v:.1f}%" for k, v in pct.items() if v > 0.1]
    conv_str = " / ".join(parts) if parts else "(none)"
    bio = "AER" if pct.get("AND", 0) + pct.get("WWT", 0) > 30 else "ENZ"
    mech = "SHR"
    rec = "CEN 100.0%" if pct.get("HTL", 0) > 0.1 else "-"
    upg = "ABS 100.0%" if pct.get("AND", 0) > 0.1 else "-"
    return f"Conv: {conv_str} | Bio={bio} | Mech={mech} | HTLrec: {rec} | GasUpg: {upg} | STB=no"


def gen_pareto_all_scenarios():
    rows = []
    for scenario, (nac_lo, nac_hi, ghg_lo, ghg_hi, ep_lo, ep_hi) in SCENARIO_ANCHORS.items():
        point_num = 0
        for i in range(GRID_N):
            for j in range(GRID_N):
                point_num += 1
                t = i / (GRID_N - 1)   # 0 = tight GHG cap, 1 = loose
                u = j / (GRID_N - 1)   # 0 = tight EP cap,  1 = loose
                ghg_eps = round(ghg_lo + t * (ghg_hi - ghg_lo), 4)
                n_eps = round(ep_lo + u * (ep_hi - ep_lo), 4)
                # cost falls as allowances loosen, plus a little noise
                noise = random.uniform(-0.15, 0.15)
                nac = round(nac_hi - (t * 0.6 + u * 0.4) * (nac_hi - nac_lo) + noise, 4)
                ghg = round(ghg_lo + t * (ghg_hi - ghg_lo) * random.uniform(0.85, 1.0), 4)
                ep = round(ep_lo + u * (ep_hi - ep_lo) * random.uniform(0.85, 1.0), 4)
                pct = blend_for(t, u)
                quality = "Optimal" if random.random() > 0.12 else "Feasible—not proven optimal"
                row = {
                    "Scenario": scenario, "Point": f"g{point_num}",
                    "GHG_eps": ghg_eps, "N_eps": n_eps,
                    "NAC_MUSD_per_yr": nac, "GHG_tCO2e_per_yr": ghg, "EP_marine_tpy": ep,
                    "Status": "ModelStatus.OptimalGlobal" if quality == "Optimal" else "ModelStatus.Integer",
                    "Quality": quality, "Config": format_blend(pct),
                    "pct_HTL": pct["HTL"], "pct_AND": pct["AND"], "pct_SLF": pct["SLF"],
                    "pct_CMP": pct["CMP"], "pct_WWT": pct["WWT"], "pct_INC": pct["INC"],
                    "pct_HTLrec_CEN": 100.0 if pct["HTL"] > 0.1 else 0.0,
                    "pct_HTLrec_FLT": 0.0,
                    "pct_GasUpg_ABS": 100.0 if pct["AND"] > 0.1 else 0.0,
                    "pct_GasUpg_PSA": 0.0,
                }
                rows.append(row)
    return rows


def gen_scenario_comparison(pareto_rows):
    # "the" comparison = cheapest (min NAC) point per scenario, standing in
    # for the notebook's separate min-NAC blend solve (Cell 85).
    best = {}
    for row in pareto_rows:
        s = row["Scenario"]
        if s not in best or row["NAC_MUSD_per_yr"] < best[s]["NAC_MUSD_per_yr"]:
            best[s] = row
    rows = []
    for scenario in SCENARIO_ANCHORS:
        r = best[scenario]
        rows.append({
            "Scenario": scenario, "Status": "ModelStatus.OptimalGlobal",
            "Config": r["Config"], "NAC_M$/yr": r["NAC_MUSD_per_yr"],
            "GHG_tCO2e/yr": r["GHG_tCO2e_per_yr"], "EP_marine_tN-eq/yr": r["EP_marine_tpy"],
        })
    return rows


# ---------------------------------------------------------------------------
# Cost breakdown per scenario -- splits each scenario's cheapest-point NAC
# into the cost categories the notebook's costing cell actually computes
# (Capital_eq/ACC_eq, Overhead_eq+INS_eq, Labor_eq, Utility_eq, CCRM+disposal,
# WC_eq). The SPLIT PERCENTAGES below are placeholder process-cost rules of
# thumb (NOT derived from a real solve) -- they just give the Cost
# Specifications page something realistic-shaped to show per scenario until
# the notebook exports the real CCAC/CCLB/CCUC/CCOC/CCRM/CCWC values.
# ---------------------------------------------------------------------------
COST_CATEGORY_BASE_PCT = {
    "Capital_MUSD_per_yr": 0.42,
    "Overhead_MUSD_per_yr": 0.18,
    "Labor_MUSD_per_yr": 0.15,
    "Utilities_MUSD_per_yr": 0.10,
    "Materials_MUSD_per_yr": 0.10,
    "WorkingCapital_MUSD_per_yr": 0.05,
}


def gen_cost_breakdown(comparison_rows):
    rows = []
    for r in comparison_rows:
        nac = r["NAC_M$/yr"]
        # small per-scenario jitter so the split isn't identical everywhere,
        # then renormalize so the components still sum to NAC exactly.
        jittered = {k: max(0.01, v + random.uniform(-0.03, 0.03))
                    for k, v in COST_CATEGORY_BASE_PCT.items()}
        total_pct = sum(jittered.values())
        row = {"Scenario": r["Scenario"]}
        for key, pct in jittered.items():
            row[key] = round(nac * pct / total_pct, 4)
        row["NAC_MUSD_per_yr"] = nac
        rows.append(row)
    return rows


def write_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {path} ({len(rows)} rows)")


if __name__ == "__main__":
    pareto_rows = gen_pareto_all_scenarios()
    write_csv("data/pareto_all_scenarios.csv", pareto_rows)

    comparison_rows = gen_scenario_comparison(pareto_rows)
    write_csv("data/scenario_comparison.csv", comparison_rows)

    feed_rows = [{"Scenario": s, **vals} for s, vals in FEEDSTOCKS.items()]
    write_csv("data/feedstock_composition.csv", feed_rows)

    cost_rows = gen_cost_breakdown(comparison_rows)
    write_csv("data/cost_breakdown.csv", cost_rows)
