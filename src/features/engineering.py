"""
Feature engineering for GlucoTwin.

At each time point t we build a single feature vector that FUSES:

  * dynamic features  -- summaries of the last `window_min` minutes of the
                         CGM + wearable streams (trend, variability, activity,
                         sleep debt, HRV) ;
  * static features   -- the patient's EHR row (labs, meds, comorbidities,
                         demographics, genetic-risk proxy).

The fusion is a late concatenation: dynamic window features || static EHR
features. The ablation study in models/train.py toggles which blocks are
included, to measure what each stream adds.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

STEP_MINUTES = 15

STATIC_NUMERIC = [
    "age",
    "bmi",
    "diabetes_duration_years",
    "hba1c",
    "fasting_glucose",
    "family_history_diabetes",
    "on_metformin",
    "on_sulfonylurea",
    "on_insulin",
    "hypertension",
    "ckd",
    "retinopathy",
]


def _window_features(w: pd.DataFrame) -> dict:
    """Summarise one trailing window of the dynamic streams."""
    g = w["glucose"].to_numpy()
    hr = w["heart_rate"].to_numpy()
    hrv = w["hrv"].to_numpy()
    steps = w["steps"].to_numpy()
    # linear slope of glucose over the window (mg/dL per sample)
    if len(g) >= 2:
        slope = np.polyfit(np.arange(len(g)), g, 1)[0]
    else:
        slope = 0.0
    return {
        "cgm_last": g[-1],
        "cgm_mean": g.mean(),
        "cgm_std": g.std(),
        "cgm_min": g.min(),
        "cgm_max": g.max(),
        "cgm_slope": slope,
        "cgm_range": g.max() - g.min(),
        "cgm_time_above_140": float((g > 140).mean()),
        "hr_mean": hr.mean(),
        "hr_max": hr.max(),
        "hrv_mean": hrv.mean(),
        "hrv_min": hrv.min(),
        "steps_sum": steps.sum(),
        "steps_recent": steps[-4:].sum() if len(steps) >= 4 else steps.sum(),
        "sleep_frac": float((w["sleep_stage"] > 0).mean()),
        "carbs_sum": w["carbs"].sum(),
        "hour": w["hour"].iloc[-1],
    }


def build_feature_table(
    ehr: pd.DataFrame,
    ts: pd.DataFrame,
    window_min: int = 120,
    stride: int = 2,
) -> pd.DataFrame:
    """Create the fused feature table (one row per sampled time point).

    `stride` sub-samples time points to keep the table compact (stride=2 -> a
    training row every 30 minutes). Rows without a full trailing window are
    skipped."""
    win = window_min // STEP_MINUTES
    ehr_idx = ehr.set_index("patient_id")
    rows = []
    for pid, grp in ts.groupby("patient_id", sort=False):
        grp = grp.sort_values("t_index").reset_index(drop=True)
        static = ehr_idx.loc[pid]
        static_feats = {f"ehr_{k}": static[k] for k in STATIC_NUMERIC}
        for i in range(win, len(grp), stride):
            w = grp.iloc[i - win : i]
            feats = _window_features(w)
            feats.update(static_feats)
            feats["patient_id"] = pid
            feats["t_index"] = int(grp["t_index"].iloc[i])
            feats["label"] = int(grp["future_hyper_event"].iloc[i])
            rows.append(feats)
    table = pd.DataFrame(rows)
    return table


def feature_columns(table: pd.DataFrame) -> dict:
    """Split columns into dynamic vs static blocks (for ablation)."""
    dynamic = [
        c
        for c in table.columns
        if not c.startswith("ehr_") and c not in ("patient_id", "t_index", "label")
    ]
    static = [c for c in table.columns if c.startswith("ehr_")]
    return {"dynamic": dynamic, "static": static}
