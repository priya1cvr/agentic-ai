"""
SLA Predictor
-------------
Estimates the probability that an app's duration will breach its configured
SLA, using the trailing 30-day duration distribution (mean/stddev) as a
model of "normal" behavior for that job, rather than a single hardcoded
duration threshold. This catches slow drift (job creeping from 20min -> 35min
over a month) as well as one-off spikes.

Approach: model duration_sec ~ Normal(mean, stddev) from history, then compute
P(duration > sla_seconds) via the normal CDF. Deliberately simple/explainable
over a heavier time-series model -- swap in Prophet/ARIMA later if the
heuristic proves too coarse for a given job family.
"""
import math
from typing import Optional


def _normal_cdf(x: float, mean: float, stddev: float) -> float:
    if stddev <= 0:
        return 1.0 if x >= mean else 0.0
    z = (x - mean) / (stddev * math.sqrt(2))
    return 0.5 * (1 + math.erf(z))


def predict_sla_breach(
    app_name: str,
    duration_sec: float,
    state: str,
    hist_mean_sec: Optional[float],
    hist_stddev_sec: Optional[float],
    n_hist_runs: int,
    sla_minutes: float,
    min_history_runs: int = 5,
) -> dict:
    sla_sec = sla_minutes * 60

    if state == "RUNNING":
        # already past SLA and still running = certain breach
        if duration_sec >= sla_sec:
            return _result(app_name, duration_sec, sla_sec, 1.0, "CRITICAL", "already exceeded SLA and still running")
        if not hist_mean_sec or n_hist_runs < min_history_runs:
            return _result(app_name, duration_sec, sla_sec, None, "INFO", "insufficient history to predict")
        prob_breach = 1 - _normal_cdf(sla_sec, hist_mean_sec, hist_stddev_sec or hist_mean_sec * 0.15)
        severity = _severity_for(prob_breach)
        return _result(app_name, duration_sec, sla_sec, prob_breach, severity,
                        f"in-flight, historical mean {hist_mean_sec / 60:.1f}min vs SLA {sla_minutes}min")

    # finished (success/failed/killed) -- report actual breach, not a prediction
    if duration_sec > sla_sec:
        overrun_pct = (duration_sec - sla_sec) / sla_sec * 100
        return _result(app_name, duration_sec, sla_sec, 1.0, "CRITICAL",
                        f"breached SLA by {overrun_pct:.0f}% ({duration_sec/60:.1f}min vs {sla_minutes}min)")
    return _result(app_name, duration_sec, sla_sec, 0.0, "INFO", "within SLA")


def _severity_for(prob: float) -> str:
    if prob >= 0.8:
        return "CRITICAL"
    if prob >= 0.5:
        return "WARNING"
    return "INFO"


def _result(app_name, duration_sec, sla_sec, prob_breach, severity, note) -> dict:
    return {
        "app_name": app_name,
        "duration_sec": duration_sec,
        "sla_sec": sla_sec,
        "breach_probability": prob_breach,
        "severity": severity,
        "note": note,
    }
