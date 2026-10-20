"""
Explainability for GlucoTwin.

A clinician will not trust a black box. For every risk score we expose the
features that drove it, using SHAP when available and a model-agnostic
permutation / contribution fallback otherwise. The dashboard renders these as
"why is this patient at risk right now" bars.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

try:
    import shap  # type: ignore

    _HAS_SHAP = True
except Exception:  # pragma: no cover
    _HAS_SHAP = False


def global_importance(model, X: pd.DataFrame) -> pd.Series:
    """Mean |contribution| per feature across a sample (global view)."""
    if _HAS_SHAP:
        try:
            explainer = shap.TreeExplainer(model)
            vals = explainer.shap_values(X)
            if isinstance(vals, list):
                vals = vals[1]
            imp = np.abs(vals).mean(axis=0)
            return pd.Series(imp, index=X.columns).sort_values(ascending=False)
        except Exception:
            pass
    # fallback: native feature_importances_ or permutation
    if hasattr(model, "feature_importances_"):
        return pd.Series(model.feature_importances_, index=X.columns).sort_values(ascending=False)
    from sklearn.inspection import permutation_importance

    # needs y; approximate with variance of predictions when unavailable
    base = model.predict_proba(X)[:, 1]
    imps = {}
    rng = np.random.default_rng(0)
    for col in X.columns:
        Xp = X.copy()
        Xp[col] = rng.permutation(Xp[col].to_numpy())
        imps[col] = np.abs(model.predict_proba(Xp)[:, 1] - base).mean()
    return pd.Series(imps).sort_values(ascending=False)


def local_explanation(model, x_row: pd.DataFrame, top_k: int = 6) -> pd.Series:
    """Per-prediction contributions for a single patient/time point."""
    if _HAS_SHAP:
        try:
            explainer = shap.TreeExplainer(model)
            vals = explainer.shap_values(x_row)
            if isinstance(vals, list):
                vals = vals[1]
            s = pd.Series(np.asarray(vals).ravel(), index=x_row.columns)
            return s.reindex(s.abs().sort_values(ascending=False).index)[:top_k]
        except Exception:
            pass
    # fallback: one-feature-at-a-time delta vs cohort median
    base = model.predict_proba(x_row)[:, 1][0]
    contrib = {}
    for col in x_row.columns:
        xp = x_row.copy()
        xp[col] = 0
        contrib[col] = base - model.predict_proba(xp)[:, 1][0]
    s = pd.Series(contrib)
    return s.reindex(s.abs().sort_values(ascending=False).index)[:top_k]
