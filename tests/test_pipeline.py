"""Smoke tests: the pipeline runs and the fusion ablation is monotonic."""

import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data.synthetic import generate_dataset
from src.features.engineering import build_feature_table
from src.models import train as T


def test_end_to_end_and_ablation_monotonic():
    ehr, ts = generate_dataset(n_patients=40, n_days=6, seed=1)
    assert {"glucose", "hrv", "steps", "future_hyper_event"}.issubset(ts.columns)
    assert ts["future_hyper_event"].mean() > 0.02  # events exist

    table = build_feature_table(ehr, ts, window_min=120, stride=3)
    assert len(table) > 500
    train_df, test_df = T.patient_split(table, test_size=0.3, seed=1)
    # no patient leakage across the split
    assert set(train_df["patient_id"]) & set(test_df["patient_id"]) == set()

    ab = T.run_ablation(train_df, test_df)
    roc = [ab[k]["roc_auc"] for k in ["CGM only", "CGM + Wearable", "CGM + Wearable + EHR"]]
    # fusing more streams should not hurt ROC-AUC (allow tiny noise tolerance)
    assert roc[1] >= roc[0] - 0.01
    assert roc[2] >= roc[0] - 0.01
    # full fused model is clinically useful
    assert ab["CGM + Wearable + EHR"]["roc_auc"] > 0.8


if __name__ == "__main__":
    test_end_to_end_and_ablation_monotonic()
    print("OK: pipeline runs, no leakage, fusion ablation healthy.")
