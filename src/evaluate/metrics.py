"""
Clinically-literate evaluation for GlucoTwin.

We deliberately do NOT lead with raw accuracy. For an early-warning system a
clinician cares about:

  * how far ahead we warn (lead time),
  * how many true events we catch at a tolerable false-alarm rate
    (sensitivity @ fixed false-alarm-rate),
  * whether the probabilities are trustworthy (calibration / Brier),
  * for the glucose forecast, whether errors are clinically safe
    (Clarke Error Grid zones).
"""

from __future__ import annotations

import numpy as np
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    roc_auc_score,
)

STEP_MINUTES = 15


def classification_metrics(y_true: np.ndarray, y_prob: np.ndarray) -> dict:
    out = {
        "roc_auc": float(roc_auc_score(y_true, y_prob)) if len(np.unique(y_true)) > 1 else float("nan"),
        "pr_auc": float(average_precision_score(y_true, y_prob)) if y_true.sum() > 0 else float("nan"),
        "brier": float(brier_score_loss(y_true, y_prob)),
        "event_rate": float(y_true.mean()),
    }
    return out


def sensitivity_at_far(y_true: np.ndarray, y_prob: np.ndarray, target_far: float = 0.10) -> dict:
    """Pick the threshold whose false-alarm rate (FP / negatives) is closest to
    target_far, then report the sensitivity (recall) achieved there."""
    neg = y_true == 0
    pos = y_true == 1
    if neg.sum() == 0 or pos.sum() == 0:
        return {"threshold": float("nan"), "sensitivity": float("nan"), "far": float("nan")}
    thresholds = np.unique(y_prob)
    best = None
    for thr in thresholds:
        pred = y_prob >= thr
        far = pred[neg].mean()
        sens = pred[pos].mean()
        if best is None or abs(far - target_far) < abs(best["far"] - target_far):
            best = {"threshold": float(thr), "sensitivity": float(sens), "far": float(far)}
    return best


def lead_time_minutes(
    y_true_seq: np.ndarray,
    y_prob_seq: np.ndarray,
    threshold: float,
    base_horizon_min: int = 60,
    max_lookback_steps: int = 8,
) -> float:
    """Average warning lead time across detected events.

    The label at time t already means 'a hyperglycemic excursion occurs
    60-120 min from now', so a correct alarm at t warns at least `base_horizon`
    minutes ahead. For each event onset (0->1 transition) that we alarm on, we
    additionally credit the consecutive earlier steps whose risk was already
    above threshold -> extra lead time. Events never alarmed are counted as a
    miss (0 min) so the number is not optimistic."""
    alarms = y_prob_seq >= threshold
    n = len(y_true_seq)
    leads = []
    for j in range(n):
        onset = y_true_seq[j] == 1 and (j == 0 or y_true_seq[j - 1] == 0)
        if not onset:
            continue
        if not alarms[j]:
            leads.append(0.0)  # missed this event entirely
            continue
        extra = 0
        k = j - 1
        while k >= 0 and alarms[k] and extra < max_lookback_steps:
            extra += 1
            k -= 1
        leads.append(base_horizon_min + extra * STEP_MINUTES)
    return float(np.mean(leads)) if leads else float("nan")


# --------------------------------------------------------------------------- #
# Clarke Error Grid -- for the glucose-value forecast
# --------------------------------------------------------------------------- #
def clarke_zone(ref: float, pred: float) -> str:
    """Return the Clarke Error Grid zone ('A'..'E') for one (reference, predicted)
    glucose pair in mg/dL. Standard Clarke (1987) boundaries."""
    if (ref <= 70 and pred <= 70) or (abs(pred - ref) <= 0.2 * ref):
        return "A"
    if (ref >= 180 and pred <= 70) or (ref <= 70 and pred >= 180):
        return "E"
    if ((70 <= ref <= 290) and pred >= ref + 110) or ((130 <= ref <= 180) and pred <= (7 / 5) * ref - 182):
        return "C"
    if (
        (ref >= 240 and 70 <= pred <= 180)
        or (ref <= 70 <= pred and pred <= 180)
        or (70 <= ref <= 180 and pred >= 180)
    ):
        return "D"
    return "B"


def clarke_grid_summary(ref: np.ndarray, pred: np.ndarray) -> dict:
    zones = [clarke_zone(r, p) for r, p in zip(ref, pred)]
    total = len(zones)
    counts = {z: zones.count(z) / total for z in ["A", "B", "C", "D", "E"]}
    counts["AB_fraction"] = counts["A"] + counts["B"]  # clinically acceptable
    counts["rmse"] = float(np.sqrt(np.mean((ref - pred) ** 2)))
    counts["mae"] = float(np.mean(np.abs(ref - pred)))
    return counts
