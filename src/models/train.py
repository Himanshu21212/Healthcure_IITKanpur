"""
Training, ablation and evaluation for GlucoTwin.

Deployed predictor: gradient-boosted trees on the fused (window || EHR) feature
vector -- interpretable, fast, SHAP-friendly. An optional LSTM sequence encoder
lives in models/sequence_model.py and is trained by run.py when PyTorch is
installed; the tree model is the always-on backbone that powers the dashboard.

The main experiment is a 3-way ablation, to check that each stream helps:

    CGM only  ->  CGM + Wearable  ->  CGM + Wearable + EHR

Each added stream should lift ROC-AUC, PR-AUC and sensitivity@FAR.
"""

from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.model_selection import GroupShuffleSplit

from src.evaluate.metrics import (
    classification_metrics,
    clarke_grid_summary,
    lead_time_minutes,
    sensitivity_at_far,
)

try:  # prefer XGBoost if the user installed it; otherwise fall back cleanly
    from xgboost import XGBClassifier  # noqa: F401

    _HAS_XGB = True
except Exception:  # pragma: no cover
    _HAS_XGB = False


def _column_groups(cols: list[str]) -> dict:
    cgm = [c for c in cols if c.startswith("cgm_") or c in ("carbs_sum", "hour")]
    wearable = [
        c
        for c in cols
        if c.startswith("hr_") or c.startswith("hrv_") or c.startswith("steps_") or c == "sleep_frac"
    ]
    static = [c for c in cols if c.startswith("ehr_")]
    return {"cgm": cgm, "wearable": wearable, "static": static}


def _make_classifier():
    if _HAS_XGB:
        from xgboost import XGBClassifier

        return XGBClassifier(
            n_estimators=300,
            max_depth=5,
            learning_rate=0.05,
            subsample=0.9,
            colsample_bytree=0.9,
            eval_metric="logloss",
            n_jobs=4,
        )
    return HistGradientBoostingClassifier(
        max_iter=300, learning_rate=0.06, max_depth=6, l2_regularization=1.0, random_state=0
    )


def patient_split(table: pd.DataFrame, test_size: float = 0.25, seed: int = 0):
    gss = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=seed)
    train_idx, test_idx = next(gss.split(table, groups=table["patient_id"]))
    return table.iloc[train_idx].copy(), table.iloc[test_idx].copy()


def run_ablation(train: pd.DataFrame, test: pd.DataFrame) -> dict:
    feature_cols = [c for c in train.columns if c not in ("patient_id", "t_index", "label")]
    groups = _column_groups(feature_cols)

    configs = {
        "CGM only": groups["cgm"],
        "CGM + Wearable": groups["cgm"] + groups["wearable"],
        "CGM + Wearable + EHR": groups["cgm"] + groups["wearable"] + groups["static"],
    }

    y_train = train["label"].to_numpy()
    y_test = test["label"].to_numpy()
    results = {}
    for name, cols in configs.items():
        clf = _make_classifier()
        clf.fit(train[cols], y_train)
        prob = clf.predict_proba(test[cols])[:, 1]
        m = classification_metrics(y_test, prob)
        saf = sensitivity_at_far(y_test, prob, target_far=0.10)
        m["sensitivity_at_10pct_far"] = saf["sensitivity"]
        m["n_features"] = len(cols)
        results[name] = m
    return results


def train_full_models(train: pd.DataFrame, test: pd.DataFrame, ts: pd.DataFrame):
    """Train the deployed classifier (full fusion) + a glucose forecaster, and
    return everything the dashboard and the error grid need."""
    feature_cols = [c for c in train.columns if c not in ("patient_id", "t_index", "label")]

    # --- deployed event classifier (full fusion) ---
    clf = _make_classifier()
    clf.fit(train[feature_cols], train["label"].to_numpy())
    test_prob = clf.predict_proba(test[feature_cols])[:, 1]

    y_test = test["label"].to_numpy()
    base_metrics = classification_metrics(y_test, test_prob)
    saf = sensitivity_at_far(y_test, test_prob, target_far=0.10)
    base_metrics.update(
        {
            "sensitivity_at_10pct_far": saf["sensitivity"],
            "operating_threshold": saf["threshold"],
            "operating_far": saf["far"],
        }
    )

    # --- lead time: evaluate across the whole test set, concatenated per patient ---
    # pick the test patient with the most events so lead time is well-defined
    ev_by_pid = test.groupby("patient_id")["label"].sum()
    rep_pid = ev_by_pid.sort_values(ascending=False).index[0]
    rep = test[test["patient_id"] == rep_pid].sort_values("t_index")
    rep_prob = clf.predict_proba(rep[feature_cols])[:, 1]
    base_metrics["mean_lead_time_min"] = lead_time_minutes(
        rep["label"].to_numpy(), rep_prob, saf["threshold"]
    )

    # --- glucose forecaster (+60 min) for the Clarke error grid ---
    fc_table = _forecast_table(ts, feature_source=train, test_source=test)
    reg = HistGradientBoostingRegressor(max_iter=250, learning_rate=0.06, random_state=0)
    reg.fit(fc_table["train_X"], fc_table["train_y"])
    pred_future = reg.predict(fc_table["test_X"])
    grid = clarke_grid_summary(fc_table["test_y"], pred_future)

    return {
        "classifier": clf,
        "regressor": reg,
        "feature_cols": feature_cols,
        "test_prob": test_prob,
        "base_metrics": base_metrics,
        "error_grid": grid,
        "forecast": {"ref": fc_table["test_y"], "pred": pred_future},
        "operating_threshold": saf["threshold"],
    }


def _forecast_table(ts: pd.DataFrame, feature_source: pd.DataFrame, test_source: pd.DataFrame):
    """Build a compact +60min glucose-forecast table aligned to the same
    patient train/test split (uses current window stats -> future glucose)."""
    train_pids = set(feature_source["patient_id"].unique())
    test_pids = set(test_source["patient_id"].unique())
    horizon = 60 // 15
    rows = []
    for pid, grp in ts.groupby("patient_id", sort=False):
        grp = grp.sort_values("t_index").reset_index(drop=True)
        g = grp["glucose"].to_numpy()
        hrv = grp["hrv"].to_numpy()
        steps = grp["steps"].to_numpy()
        carbs = grp["carbs"].to_numpy()
        hour = grp["hour"].to_numpy()
        for i in range(8, len(grp) - horizon, 4):
            w = g[i - 8 : i]
            rows.append(
                {
                    "patient_id": pid,
                    "g_last": w[-1],
                    "g_lag1": w[-2],
                    "g_lag2": w[-3],
                    "g_mean": w.mean(),
                    "g_std": w.std(),
                    "g_slope": np.polyfit(np.arange(len(w)), w, 1)[0],
                    "hrv_mean": hrv[i - 8 : i].mean(),
                    "steps_sum": steps[i - 8 : i].sum(),
                    "carbs_recent": carbs[i - 8 : i].sum(),
                    "hour_sin": np.sin(2 * np.pi * hour[i] / 24),
                    "hour_cos": np.cos(2 * np.pi * hour[i] / 24),
                    "y_future": g[i + horizon],
                }
            )
    df = pd.DataFrame(rows)
    feat = ["g_last", "g_lag1", "g_lag2", "g_mean", "g_std", "g_slope",
            "hrv_mean", "steps_sum", "carbs_recent", "hour_sin", "hour_cos"]
    tr = df[df["patient_id"].isin(train_pids)]
    te = df[df["patient_id"].isin(test_pids)]
    return {
        "train_X": tr[feat],
        "train_y": tr["y_future"].to_numpy(),
        "test_X": te[feat],
        "test_y": te["y_future"].to_numpy(),
    }


def save_report(path: str, ablation: dict, full: dict, meta: dict):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    report = {
        "meta": meta,
        "ablation": ablation,
        "full_model": full["base_metrics"],
        "error_grid": full["error_grid"],
        "backend": "xgboost" if _HAS_XGB else "sklearn-histgb",
    }
    with open(path, "w") as f:
        json.dump(report, f, indent=2)
    return report
