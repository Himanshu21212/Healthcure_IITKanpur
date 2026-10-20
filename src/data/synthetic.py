"""
Synthetic data engine for GlucoTwin.

Generates two fused data streams for a cohort of virtual Type-2-Diabetes patients:

  1. STATIC / HISTORICAL  (Electronic Health Record)
     demographics, comorbidities, medications, labs, family history.

  2. DYNAMIC / REAL-TIME  (consumer wearable + CGM time-series)
     continuous glucose, heart rate, heart-rate variability (HRV),
     steps, sleep stage, meal events -- sampled every 15 minutes.

The two streams are linked through a latent, per-patient `glycemic_instability`
score derived from the EHR. That score drives how violently the dynamic glucose
trace reacts to meals and how protective activity/sleep are, so neither
stream alone is enough to predict an excursion.

Everything is reproducible from a single seed. No real patient data is used,
in line with the DPDP Act (India) and HIPAA.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# 15-minute sampling -> 96 samples per day
SAMPLES_PER_DAY = 96
STEP_MINUTES = 15

# India-relevant T2D cohort priors (approximate, for simulation only)
ETHNICITY_SUBGROUPS = ["North Indian", "South Indian", "East Indian", "West Indian"]


def _sigmoid(x: np.ndarray | float) -> np.ndarray | float:
    return 1.0 / (1.0 + np.exp(-x))


# --------------------------------------------------------------------------- #
# 1. STATIC STREAM  -- synthetic Electronic Health Records
# --------------------------------------------------------------------------- #
def generate_ehr(n_patients: int, seed: int = 42) -> pd.DataFrame:
    """Return one row per virtual patient with EHR features + a latent
    glycemic_instability score used by the dynamic generator."""
    rng = np.random.default_rng(seed)

    age = np.clip(rng.normal(54, 11, n_patients), 28, 85).round(0)
    sex = rng.choice(["M", "F"], n_patients, p=[0.55, 0.45])
    ethnicity = rng.choice(ETHNICITY_SUBGROUPS, n_patients)

    # Indian T2D patients skew toward higher central adiposity at lower BMI
    bmi = np.clip(rng.normal(27.5, 4.2, n_patients), 17, 44).round(1)

    diabetes_duration = np.clip(rng.exponential(6.0, n_patients), 0.3, 32).round(1)
    family_history = rng.choice([0, 1], n_patients, p=[0.45, 0.55])  # genetic-risk proxy

    # HbA1c driven by duration, BMI, family history
    hba1c = (
        6.3
        + 0.09 * diabetes_duration
        + 0.05 * (bmi - 25)
        + 0.4 * family_history
        + rng.normal(0, 0.6, n_patients)
    )
    hba1c = np.clip(hba1c, 5.4, 13.5).round(1)

    fasting_glucose = np.clip(28 * hba1c - 50 + rng.normal(0, 12, n_patients), 80, 260).round(0)

    # Medications (more likely with longer duration / higher HbA1c)
    p_metformin = _sigmoid(0.9 * (hba1c - 6.5))
    on_metformin = (rng.random(n_patients) < p_metformin).astype(int)
    p_sulfonylurea = _sigmoid(0.8 * (hba1c - 7.5))
    on_sulfonylurea = (rng.random(n_patients) < p_sulfonylurea).astype(int)
    p_insulin = _sigmoid(1.1 * (hba1c - 8.5))
    on_insulin = (rng.random(n_patients) < p_insulin).astype(int)

    # Comorbidities
    hypertension = (rng.random(n_patients) < _sigmoid(0.07 * (age - 50) + 0.1 * (bmi - 25))).astype(int)
    ckd = (rng.random(n_patients) < _sigmoid(0.08 * (diabetes_duration - 8))).astype(int)
    retinopathy = (rng.random(n_patients) < _sigmoid(0.10 * (diabetes_duration - 10))).astype(int)

    # Latent glycemic instability (0..1): how brittle the patient's glucose is.
    # Higher HbA1c, longer duration, insulin use, lower treatment -> more brittle.
    instability_raw = (
        0.35 * (hba1c - 6.0) / 7.0
        + 0.20 * diabetes_duration / 30.0
        + 0.15 * on_insulin
        + 0.10 * (bmi - 20) / 24.0
        + 0.10 * family_history
        - 0.08 * on_metformin
        + rng.normal(0, 0.05, n_patients)
    )
    glycemic_instability = np.clip(instability_raw, 0.05, 0.98)

    ehr = pd.DataFrame(
        {
            "patient_id": [f"P{idx:04d}" for idx in range(n_patients)],
            "age": age.astype(int),
            "sex": sex,
            "ethnicity": ethnicity,
            "bmi": bmi,
            "diabetes_duration_years": diabetes_duration,
            "hba1c": hba1c,
            "fasting_glucose": fasting_glucose.astype(int),
            "family_history_diabetes": family_history,
            "on_metformin": on_metformin,
            "on_sulfonylurea": on_sulfonylurea,
            "on_insulin": on_insulin,
            "hypertension": hypertension,
            "ckd": ckd,
            "retinopathy": retinopathy,
            "glycemic_instability": glycemic_instability.round(3),
        }
    )
    return ehr


# --------------------------------------------------------------------------- #
# 2. DYNAMIC STREAM -- CGM + wearable time-series
# --------------------------------------------------------------------------- #
def _simulate_patient_timeseries(
    patient: pd.Series, n_days: int, rng: np.random.Generator
) -> pd.DataFrame:
    """Simulate a coupled CGM + wearable trace for one patient.

    Design note (why fusion helps): the adverse event is a post-meal spike that
    happens in the NEAR FUTURE, so the trailing CGM window cannot see the meal
    itself. Whether an upcoming meal spikes past 180 mg/dL is governed by a
    latent insulin-resistance state IR(t). IR shares a hidden stress process
    with HRV (so the wearable stream is informative about it) and is anchored by
    the patient's EHR instability (so the static stream is informative too).
    Hence: CGM alone -> partial signal; +wearable reveals IR fluctuations;
    +EHR reveals IR's baseline. Each stream adds genuine predictive value.
    """
    n = n_days * SAMPLES_PER_DAY
    t = np.arange(n)
    minute_of_day = (t * STEP_MINUTES) % (24 * 60)
    hour = minute_of_day / 60.0

    instab = patient["glycemic_instability"]
    # Weak instability->baseline coupling on purpose: we do NOT want the current
    # glucose level to leak the patient's instability, or CGM alone would already
    # know everything. Instability instead acts through the meal-spike magnitude.
    base_glucose = 98 + 8 * instab + 0.08 * (patient["fasting_glucose"] - 110)

    # --- Sleep: block of sleep roughly 23:00 -> 07:00 ---
    is_night = ((hour >= 23) | (hour < 7)).astype(float)
    night_index = ((t * STEP_MINUTES) // (24 * 60)).astype(int)
    nightly_quality = rng.uniform(0.4, 1.0, size=n_days)[np.clip(night_index, 0, n_days - 1)]
    night_q = nightly_quality[np.clip(night_index, 0, n_days - 1)]
    sleep_debt = np.clip(1.0 - night_q, 0, 1) * (1 - is_night)  # daytime burden of poor sleep
    sleep_stage = np.where(
        is_night > 0,
        rng.choice([1, 2, 3, 4], size=n, p=[0.25, 0.35, 0.25, 0.15]),  # 1=light..4=REM
        0,
    )

    # --- Latent stress process s(t): AR(1), shared by HRV and IR ---
    s = np.zeros(n)
    for i in range(1, n):
        s[i] = 0.92 * s[i - 1] + rng.normal(0, 0.35)
    s = 0.6 * (s - s.mean()) / (s.std() + 1e-6)  # standardized then scaled hidden stress

    # --- Activity: step bursts during the day ---
    activity_prob = 0.12 + 0.10 * np.exp(-((hour - 8) ** 2) / 6) + 0.10 * np.exp(-((hour - 18) ** 2) / 6)
    activity_prob *= (1 - is_night)
    step_bursts = (rng.random(n) < activity_prob).astype(float)
    steps = np.clip((step_bursts * rng.gamma(3.0, 250, size=n)).round(0), 0, 4000)
    # recent activity (trailing 2h) improves insulin sensitivity
    recent_steps = pd.Series(steps).rolling(8, min_periods=1).sum().to_numpy()
    recent_act_norm = np.clip(recent_steps / 6000.0, 0, 1)

    # --- Heart rate ---
    hr_circadian = 62 + 8 * np.sin((hour - 15) / 24 * 2 * np.pi)
    heart_rate = np.clip(hr_circadian - 6 * is_night + 0.010 * steps + 4 * s + rng.normal(0, 3, n), 44, 165).round(0)

    # --- HRV (RMSSD, ms): mainly ACUTE state (stress, sleep, activity).
    # We keep its dependence on *chronic* instability weak so that the EHR stream
    # (hba1c, duration, instability) still carries unique predictive signal the
    # wearable cannot reveal -- otherwise fusing EHR would add nothing. ---
    hrv = (
        48 - 10 * instab              # weak chronic coupling (was strong -> redundant with EHR)
        + 16 * (night_q - 0.7)
        + 10 * is_night
        - 18 * s                      # shares the hidden ACUTE stress process with IR
        - 0.003 * steps
        + rng.normal(0, 3.5, n)
    )
    hrv = np.clip(hrv, 8, 120).round(1)

    # --- Latent insulin-resistance modifier IR(t), wide dynamic range ---
    # IR is the hidden driver of whether an upcoming meal spikes past 180. It is
    # anchored by EHR instability and fluctuates with stress/sleep/activity that
    # the WEARABLE stream reveals -- so both fused streams carry real signal.
    ir = (
        1.0
        + 1.8 * instab               # EHR chronic driver (unique to EHR stream)
        + 0.9 * s                    # acute stress (co-revealed by HRV, ~balanced magnitude)
        + 0.6 * sleep_debt           # wearable: poor sleep raises resistance
        - 0.8 * recent_act_norm      # wearable: recent exercise protects
        + rng.normal(0, 0.12, n)
    )
    ir = np.clip(ir, 0.40, 4.0)

    # --- Meals: circadian schedule; magnitude of spike set by IR AT MEAL TIME ---
    carbs = np.zeros(n)
    for meal_hour, spread, load in [(8, 0.45, 55), (13.5, 0.55, 75), (20.5, 0.6, 85)]:
        meal_mask = rng.random(n) < (0.7 / SAMPLES_PER_DAY) * np.exp(
            -((hour - meal_hour) ** 2) / (2 * spread**2)
        ) * SAMPLES_PER_DAY
        carbs += meal_mask * rng.uniform(0.7, 1.3, size=n) * load
    meal_flag = (carbs > 0).astype(int)

    # sharp excursion kernel over ~90 min (6 steps): spikes return to baseline
    # quickly, so a pre-meal window usually sits clean at baseline and cannot by
    # itself reveal the patient's instability -> forces reliance on EHR+wearable.
    kernel = np.array([0.45, 0.9, 1.0, 0.75, 0.45, 0.2])
    met_blunt = 1 - 0.28 * patient["on_metformin"]
    drug_blunt = 1 - 0.14 * patient["on_insulin"] - 0.08 * patient["on_sulfonylurea"]
    # CKD (an EHR-only comorbidity) slows glucose clearance -> prolongs the spike
    # tail, so a spike is more likely to stay above 180. This lever is invisible
    # to both the CGM window and the wearable, giving the EHR stream unique value.
    ckd_tail = np.array([0.15, 0.30]) if patient["ckd"] else np.array([])
    patient_kernel = np.concatenate([kernel, ckd_tail])

    excursion = np.zeros(n)
    meal_idx = np.where(carbs > 0)[0]
    for mi in meal_idx:
        # superlinear in IR: whether the spike clears 180 is decided by IR(t),
        # i.e. by the wearable+EHR context, not by carbs alone.
        peak = carbs[mi] * (ir[mi] ** 1.4) * 0.6 * met_blunt * drug_blunt
        for k, w in enumerate(patient_kernel):
            if mi + k < n:
                excursion[mi + k] += peak * w

    # --- Assemble glucose ---
    dawn = 9 * np.exp(-((hour - 5.5) ** 2) / 2.0)
    g_noise = np.zeros(n)
    for i in range(1, n):
        g_noise[i] = 0.6 * g_noise[i - 1] + rng.normal(0, 2.0)  # correlated physiological drift
    glucose = base_glucose + dawn + 7 * sleep_debt + excursion + g_noise
    glucose += rng.normal(0, 3.0, n)  # CGM measurement noise (weakens the window as a predictor)
    glucose = np.clip(glucose, 45, 400).round(0)

    ts = pd.DataFrame(
        {
            "patient_id": patient["patient_id"],
            "t_index": t,
            "minute_of_day": minute_of_day,
            "hour": hour.round(2),
            "glucose": glucose,
            "heart_rate": heart_rate,
            "hrv": hrv,
            "steps": steps,
            "sleep_stage": sleep_stage,
            "carbs": carbs.round(0),
            "meal_flag": meal_flag,
        }
    )
    return ts


def generate_timeseries(ehr: pd.DataFrame, n_days: int = 10, seed: int = 42) -> pd.DataFrame:
    """Generate the dynamic stream for every patient in `ehr`."""
    rng = np.random.default_rng(seed + 1)
    frames = []
    for _, patient in ehr.iterrows():
        frames.append(_simulate_patient_timeseries(patient, n_days, rng))
    return pd.concat(frames, ignore_index=True)


# --------------------------------------------------------------------------- #
# 3. LABELLING -- the adverse event we predict
# --------------------------------------------------------------------------- #
def label_adverse_events(
    ts: pd.DataFrame,
    horizon_min: int = 60,
    max_horizon_min: int = 120,
    threshold: float = 180.0,
) -> pd.DataFrame:
    """Binary label at time t: will a hyperglycemic excursion (glucose > threshold)
    occur between t+horizon_min and t+max_horizon_min ? (predict the spike early)."""
    lo = horizon_min // STEP_MINUTES
    hi = max_horizon_min // STEP_MINUTES
    out = []
    for pid, grp in ts.groupby("patient_id", sort=False):
        grp = grp.sort_values("t_index").reset_index(drop=True)
        g = grp["glucose"].to_numpy()
        label = np.zeros(len(grp), dtype=int)
        for i in range(len(grp)):
            future = g[i + lo : i + hi + 1]
            if len(future) > 0 and future.max() > threshold:
                label[i] = 1
        grp["future_hyper_event"] = label
        out.append(grp)
    return pd.concat(out, ignore_index=True)


def generate_dataset(
    n_patients: int = 120, n_days: int = 10, seed: int = 42
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Convenience: full cohort -> (ehr, labelled_timeseries)."""
    ehr = generate_ehr(n_patients, seed=seed)
    ts = generate_timeseries(ehr, n_days=n_days, seed=seed)
    ts = label_adverse_events(ts)
    return ehr, ts
