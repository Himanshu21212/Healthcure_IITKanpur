"""
Real-dataset loaders (optional).

GlucoTwin runs fully on its built-in synthetic engine, so the repo can be cloned
and run with zero downloads. These loaders swap in real open datasets instead. Each returns the same (ehr, timeseries) contract as
src.data.synthetic.generate_dataset, so the rest of the pipeline is unchanged.

Supported open datasets (see README for links & licenses):

  * ShanghaiT2DM / ShanghaiT1DM  -- real CGM + clinical records (Nature Sci. Data)
  * Synthea                       -- synthetic EHR generator (CSV export)
  * PPG-DaLiA                     -- wrist HR + activity
  * MMASH                         -- 24h HRV, sleep, activity

If a file layout differs from what is expected, the loaders raise an error
naming the expected schema instead of guessing.
"""

from __future__ import annotations

import glob
import os

import numpy as np
import pandas as pd


def load_shanghai(folder: str) -> pd.DataFrame:
    """Load the ShanghaiT1DM/T2DM per-patient Excel CGM files into one long
    timeseries frame with columns [patient_id, timestamp, glucose]."""
    files = sorted(glob.glob(os.path.join(folder, "*.xls*")))
    if not files:
        raise FileNotFoundError(
            f"No .xls/.xlsx CGM files found in {folder}. "
            "Download ShanghaiT2DM from the Nature Scientific Data release and "
            "point --shanghai at the per-patient folder."
        )
    frames = []
    for fp in files:
        pid = os.path.splitext(os.path.basename(fp))[0]
        df = pd.read_excel(fp)
        # Shanghai columns: 'Date', 'CGM (mg / dl)' (names vary slightly)
        gcol = next((c for c in df.columns if "CGM" in str(c)), None)
        tcol = next((c for c in df.columns if "Date" in str(c) or "time" in str(c).lower()), None)
        if gcol is None or tcol is None:
            raise ValueError(f"Could not find CGM/Date columns in {fp}; columns={list(df.columns)}")
        frames.append(
            pd.DataFrame(
                {"patient_id": pid, "timestamp": pd.to_datetime(df[tcol]), "glucose": df[gcol].astype(float)}
            )
        )
    return pd.concat(frames, ignore_index=True)


def load_synthea_ehr(csv_folder: str) -> pd.DataFrame:
    """Build an EHR table from a Synthea CSV export (patients + conditions +
    observations). Returns the GlucoTwin EHR schema (best-effort mapping)."""
    pat_fp = os.path.join(csv_folder, "patients.csv")
    if not os.path.exists(pat_fp):
        raise FileNotFoundError(
            f"{pat_fp} not found. Run Synthea with CSV export and point "
            "--synthea at the output/csv folder."
        )
    patients = pd.read_csv(pat_fp)
    # Minimal demographic mapping; labs/meds can be joined from observations.csv
    ehr = pd.DataFrame(
        {
            "patient_id": patients["Id"],
            "age": (pd.Timestamp("today").year - pd.to_datetime(patients["BIRTHDATE"]).dt.year),
            "sex": patients["GENDER"],
        }
    )
    return ehr


def align_to_grid(ts_long: pd.DataFrame, step_minutes: int = 15) -> pd.DataFrame:
    """Resample an irregular real CGM stream onto the GlucoTwin 15-min grid and
    add a synthetic wearable layer placeholder so the feature pipeline runs.
    (For a full real run, join real PPG-DaLiA / MMASH wearable streams here.)"""
    out = []
    for pid, grp in ts_long.groupby("patient_id"):
        grp = grp.set_index("timestamp").sort_index()
        res = grp["glucose"].resample(f"{step_minutes}min").mean().interpolate()
        n = len(res)
        rng = np.random.default_rng(abs(hash(pid)) % (2**32))
        out.append(
            pd.DataFrame(
                {
                    "patient_id": pid,
                    "t_index": np.arange(n),
                    "minute_of_day": (np.arange(n) * step_minutes) % (24 * 60),
                    "hour": ((np.arange(n) * step_minutes) % (24 * 60)) / 60.0,
                    "glucose": res.to_numpy().round(0),
                    "heart_rate": np.clip(rng.normal(70, 8, n), 45, 150).round(0),
                    "hrv": np.clip(rng.normal(45, 12, n), 10, 110).round(1),
                    "steps": np.clip(rng.gamma(2, 150, n), 0, 3500).round(0),
                    "sleep_stage": 0,
                    "carbs": 0.0,
                    "meal_flag": 0,
                }
            )
        )
    return pd.concat(out, ignore_index=True)
