"""
Counterfactual 'what-if' simulation -- the feature that makes this a TWIN,
not just a classifier.

Given a patient's current fused feature vector, we perturb controllable
lifestyle / treatment levers and re-score the risk, so a doctor can ask:

    "If this patient takes a 20-minute walk now, how much does the
     2-hour hyperglycemia risk fall?"
    "If they skip their evening metformin, how much does it rise?"

These operate on the engineered feature vector, which is why the levers map to
interpretable feature edits (steps, carbs, metformin, HRV/sleep).
"""

from __future__ import annotations

import pandas as pd

# Each lever edits the fused feature vector in a clinically sensible direction.
# Edits are typed: 'add' (absolute), 'mul' (multiplicative), 'set' (assign).
LEVERS = {
    "walk_20min": {
        "label": "Take a 20-min walk now (~2500 steps)",
        "edits": {"steps_recent": ("add", 2500), "steps_sum": ("add", 2500)},
    },
    "lighter_meal": {
        "label": "Choose a lighter, low-GI meal",
        # a lighter meal flattens the coming rise: fewer window carbs + gentler slope
        "edits": {"carbs_sum": ("mul", 0.4), "cgm_slope": ("mul", 0.5)},
    },
    "take_metformin": {
        "label": "Take metformin as prescribed",
        "edits": {"ehr_on_metformin": ("set", 1)},
    },
    "improve_recovery": {
        "label": "Improve sleep / lower stress (+HRV)",
        "edits": {"hrv_mean": ("add", 12), "hrv_min": ("add", 10), "sleep_frac": ("add", 0.1)},
    },
}


def apply_lever(x_row: pd.DataFrame, lever_key: str) -> pd.DataFrame:
    x = x_row.copy()
    for col, (op, val) in LEVERS[lever_key]["edits"].items():
        if col not in x.columns:
            continue
        if op == "add":
            x[col] = x[col] + val
        elif op == "mul":
            x[col] = x[col] * val
        elif op == "set":
            x[col] = val
    return x


def simulate(model, x_row: pd.DataFrame, feature_cols: list[str]) -> dict:
    """Return baseline risk and the risk after each lever."""
    base = float(model.predict_proba(x_row[feature_cols])[:, 1][0])
    out = {"baseline_risk": base, "scenarios": {}}
    for key, spec in LEVERS.items():
        xp = apply_lever(x_row, key)
        risk = float(model.predict_proba(xp[feature_cols])[:, 1][0])
        out["scenarios"][key] = {
            "label": spec["label"],
            "risk": risk,
            "delta": risk - base,
        }
    return out
