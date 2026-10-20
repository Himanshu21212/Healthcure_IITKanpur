"""
Optional LSTM sequence encoder with late EHR fusion.

This is the deep-learning arm of the hybrid design described in the README /
architecture diagram. It consumes the RAW last-N-step multivariate window
(glucose, HR, HRV, steps, sleep) through an LSTM, then concatenates the static
EHR vector at the dense head (late fusion) before the risk output.

It is OPTIONAL: run.py trains it only when PyTorch is installed. The gradient-
boosted tree model is the always-on backbone that powers the dashboard, so the
pipeline doesn't depend on PyTorch.
"""

from __future__ import annotations

import numpy as np

try:
    import torch
    import torch.nn as nn

    _HAS_TORCH = True
except Exception:  # pragma: no cover
    _HAS_TORCH = False


if _HAS_TORCH:

    class LSTMFusion(nn.Module):
        def __init__(self, n_dyn_features: int, n_static_features: int, hidden: int = 48):
            super().__init__()
            self.lstm = nn.LSTM(n_dyn_features, hidden, batch_first=True)
            self.head = nn.Sequential(
                nn.Linear(hidden + n_static_features, 32),
                nn.ReLU(),
                nn.Dropout(0.2),
                nn.Linear(32, 1),
            )

        def forward(self, seq, static):
            _, (h, _) = self.lstm(seq)
            z = torch.cat([h[-1], static], dim=1)
            return self.head(z).squeeze(-1)


def available() -> bool:
    return _HAS_TORCH


def train_lstm(seq_X, static_X, y, epochs: int = 8, seed: int = 0):
    """seq_X: (N, T, Fdyn), static_X: (N, Fstatic), y: (N,). Returns trained model."""
    if not _HAS_TORCH:
        raise RuntimeError("PyTorch not installed; LSTM arm unavailable.")
    torch.manual_seed(seed)
    model = LSTMFusion(seq_X.shape[2], static_X.shape[1])
    opt = torch.optim.Adam(model.parameters(), lr=1e-3)
    lossf = torch.nn.BCEWithLogitsLoss()
    seq = torch.tensor(seq_X, dtype=torch.float32)
    stat = torch.tensor(static_X, dtype=torch.float32)
    yt = torch.tensor(y, dtype=torch.float32)
    model.train()
    for _ in range(epochs):
        opt.zero_grad()
        out = model(seq, stat)
        loss = lossf(out, yt)
        loss.backward()
        opt.step()
    return model
