#!/usr/bin/env python3
"""
GlucoTwin -- one-command end-to-end pipeline.

    python run.py                 # fully synthetic, zero downloads
    python run.py --patients 200 --days 14
    python run.py --shanghai data/shanghai   # swap in real CGM (optional)

Steps: generate/ingest -> fuse features -> patient-level split -> ablation ->
train deployed models -> clinical evaluation -> SHAP -> save artifacts + plots.
Artifacts land in ./artifacts and power the Streamlit dashboard.
"""

from __future__ import annotations

import argparse
import json
import os
import warnings

warnings.filterwarnings("ignore")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.data.synthetic import generate_dataset
from src.features.engineering import build_feature_table
from src.models import train as T
from src.explain.shap_explain import global_importance

ART = "artifacts"
PLOTS = os.path.join(ART, "plots")


def _banner(msg: str):
    print("\n" + "=" * 62 + f"\n  {msg}\n" + "=" * 62)


def main():
    ap = argparse.ArgumentParser(description="GlucoTwin pipeline")
    ap.add_argument("--patients", type=int, default=160)
    ap.add_argument("--days", type=int, default=12)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--shanghai", type=str, default=None, help="folder with real Shanghai CGM files")
    args = ap.parse_args()

    os.makedirs(PLOTS, exist_ok=True)

    # ---------------------------------------------------------------- ingest
    _banner("1/6  Generating fused data streams (EHR + CGM/wearable)")
    if args.shanghai:
        from src.data.loaders import load_shanghai, align_to_grid
        from src.data.synthetic import generate_ehr, label_adverse_events

        ts_long = load_shanghai(args.shanghai)
        ts = align_to_grid(ts_long)
        pids = ts["patient_id"].unique()
        ehr = generate_ehr(len(pids), seed=args.seed)
        ehr["patient_id"] = pids  # attach synthetic EHR to real CGM ids
        ts = label_adverse_events(ts)
        source = f"ShanghaiT2DM ({len(pids)} patients) + synthetic EHR"
    else:
        ehr, ts = generate_dataset(args.patients, args.days, seed=args.seed)
        source = f"synthetic ({args.patients} patients x {args.days} days)"
    print(f"  source      : {source}")
    print(f"  timeseries  : {len(ts):,} samples")
    print(f"  event rate  : {ts['future_hyper_event'].mean():.1%} of samples precede a hyper-event")

    # --------------------------------------------------------------- features
    _banner("2/6  Engineering fused feature table (window || EHR)")
    table = build_feature_table(ehr, ts, window_min=120, stride=2)
    print(f"  feature rows: {len(table):,}  |  columns: {table.shape[1]}")

    train_df, test_df = T.patient_split(table, test_size=0.25, seed=args.seed)
    print(f"  train/test  : {train_df['patient_id'].nunique()} / {test_df['patient_id'].nunique()} patients (no leakage)")

    # --------------------------------------------------------------- ablation
    _banner("3/6  Ablation study -- proving the fusion is real")
    ablation = T.run_ablation(train_df, test_df)
    for name, m in ablation.items():
        print(f"  {name:24s} ROC-AUC={m['roc_auc']:.3f}  PR-AUC={m['pr_auc']:.3f}  "
              f"Sens@10%FAR={m['sensitivity_at_10pct_far']:.3f}")

    # ----------------------------------------------------------- full models
    _banner("4/6  Training deployed twin model + glucose forecaster")
    full = T.train_full_models(train_df, test_df, ts)
    bm = full["base_metrics"]
    print(f"  ROC-AUC={bm['roc_auc']:.3f}  PR-AUC={bm['pr_auc']:.3f}  Brier={bm['brier']:.3f}")
    print(f"  Sens@10%FAR={bm['sensitivity_at_10pct_far']:.3f}  "
          f"mean lead time={bm['mean_lead_time_min']:.0f} min")
    eg = full["error_grid"]
    print(f"  Clarke grid : Zone A+B={eg['AB_fraction']:.1%}  RMSE={eg['rmse']:.1f} mg/dL")

    # ------------------------------------------------------------- explain
    _banner("5/6  Global explainability (SHAP)")
    samp = test_df[full["feature_cols"]].sample(min(400, len(test_df)), random_state=0)
    imp = global_importance(full["classifier"], samp)
    print("  top drivers :", ", ".join(imp.head(5).index.tolist()))

    # ------------------------------------------------------------- optional LSTM
    try:
        from src.models import sequence_model as SM

        if SM.available():
            print("  PyTorch detected -> LSTM fusion arm available (see sequence_model.py)")
        else:
            print("  PyTorch not installed -> skipping optional LSTM arm (tree model is backbone)")
    except Exception:
        pass

    # --------------------------------------------------------------- save
    _banner("6/6  Saving artifacts + plots")
    import joblib

    joblib.dump(
        {
            "classifier": full["classifier"],
            "regressor": full["regressor"],
            "feature_cols": full["feature_cols"],
            "operating_threshold": full["operating_threshold"],
            "global_importance": imp,
        },
        os.path.join(ART, "model.joblib"),
    )
    ehr.to_parquet(os.path.join(ART, "ehr.parquet"))
    ts.to_parquet(os.path.join(ART, "timeseries.parquet"))
    table.to_parquet(os.path.join(ART, "features.parquet"))
    test_df.assign(risk=full["test_prob"]).to_parquet(os.path.join(ART, "test_scored.parquet"))

    meta = {"source": source, "n_patients": int(ehr["patient_id"].nunique()),
            "window_min": 120, "horizon_min": "60-120", "threshold_mgdl": 180}
    report = T.save_report(os.path.join(ART, "report.json"), ablation, full, meta)

    _make_plots(ablation, full, imp, ehr, ts, test_df)
    print(f"  wrote       : {ART}/model.joblib, report.json, *.parquet, plots/*.png")
    _banner("DONE  ->  launch the dashboard:  streamlit run dashboard/app.py")
    return report


def _make_plots(ablation, full, imp, ehr, ts, test_df):
    # 1) ablation bars
    names = list(ablation.keys())
    roc = [ablation[n]["roc_auc"] for n in names]
    sens = [ablation[n]["sensitivity_at_10pct_far"] for n in names]
    x = np.arange(len(names))
    fig, ax = plt.subplots(figsize=(7, 4.2))
    ax.bar(x - 0.2, roc, 0.4, label="ROC-AUC", color="#2563eb")
    ax.bar(x + 0.2, sens, 0.4, label="Sensitivity @10% FAR", color="#16a34a")
    ax.set_xticks(x); ax.set_xticklabels(names, rotation=12, ha="right", fontsize=9)
    ax.set_ylim(0, 1); ax.set_title("Ablation: each fused stream adds predictive power")
    ax.legend(); fig.tight_layout(); fig.savefig(os.path.join(PLOTS, "ablation.png"), dpi=130); plt.close(fig)

    # 2) Clarke error grid
    ref = full["forecast"]["ref"]; pred = full["forecast"]["pred"]
    fig, ax = plt.subplots(figsize=(5.4, 5.2))
    ax.scatter(ref, pred, s=6, alpha=0.3, color="#2563eb")
    lim = 400
    ax.plot([0, lim], [0, lim], "k--", lw=1)
    for b in (70, 180):
        ax.axhline(b, color="grey", lw=0.6, ls=":"); ax.axvline(b, color="grey", lw=0.6, ls=":")
    ax.set_xlim(0, lim); ax.set_ylim(0, lim)
    ax.set_xlabel("Reference glucose (mg/dL)"); ax.set_ylabel("Predicted +60 min (mg/dL)")
    ax.set_title(f"Clarke Error Grid  |  Zone A+B = {full['error_grid']['AB_fraction']:.1%}")
    fig.tight_layout(); fig.savefig(os.path.join(PLOTS, "error_grid.png"), dpi=130); plt.close(fig)

    # 3) global importance
    fig, ax = plt.subplots(figsize=(7, 4.6))
    top = imp.head(12)[::-1]
    ax.barh(top.index, top.values, color="#7c3aed")
    ax.set_title("Top risk drivers (SHAP global importance)"); fig.tight_layout()
    fig.savefig(os.path.join(PLOTS, "global_importance.png"), dpi=130); plt.close(fig)

    # 4) example patient trace with risk + event shading
    pid = test_df["patient_id"].value_counts().index[0]
    series = ts[ts["patient_id"] == pid].sort_values("t_index").iloc[:288]  # ~3 days
    scored = test_df[test_df["patient_id"] == pid].sort_values("t_index")
    clf = full["classifier"]; fc = full["feature_cols"]
    risk = clf.predict_proba(scored[fc])[:, 1]
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(9, 5.4), sharex=False, gridspec_kw={"height_ratios": [2, 1]})
    a1.plot(series["t_index"], series["glucose"], color="#111827", lw=1)
    a1.axhline(180, color="#dc2626", ls="--", lw=1, label="hyper threshold 180")
    a1.fill_between(series["t_index"], 180, series["glucose"], where=series["glucose"] > 180,
                    color="#fecaca", alpha=0.7)
    a1.set_ylabel("Glucose mg/dL"); a1.set_title(f"Virtual patient {pid}: glucose + model risk"); a1.legend(fontsize=8)
    a2.plot(scored["t_index"], risk, color="#ea580c", lw=1.2)
    a2.axhline(full["operating_threshold"], color="grey", ls=":", lw=1, label="alarm threshold")
    a2.set_ylabel("2h hyper risk"); a2.set_ylim(0, 1); a2.set_xlabel("time index (15-min steps)"); a2.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(os.path.join(PLOTS, "example_patient.png"), dpi=130); plt.close(fig)


if __name__ == "__main__":
    main()
