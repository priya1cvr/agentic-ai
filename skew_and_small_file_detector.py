"""
Skew & Small-File Detectors
----------------------------
Operate on StageMetric-shaped dicts (see history_collector.to_stage_metric_dicts).

Skew: a stage where the slowest task takes far longer than the median task
is the classic symptom of data skew (a hot key, uneven partitioning, etc).

Small files: a stage reading a huge number of tasks with a tiny average
input size per task usually means upstream data is fragmented into too
many small files/partitions -- expensive scheduling overhead per byte read.
"""
from typing import List


def detect_skew(stage_metrics: List[dict], app_id: str, app_name: str, run_date: str, cfg: dict) -> List[dict]:
    flags = []
    min_tasks = cfg["min_tasks_to_evaluate"]
    warn_ratio = cfg["ratio_warning"]
    crit_ratio = cfg["ratio_critical"]

    for s in stage_metrics:
        if s["num_tasks"] < min_tasks:
            continue
        ratio = s["skew_ratio"]
        if ratio >= crit_ratio:
            severity = "CRITICAL"
        elif ratio >= warn_ratio:
            severity = "WARNING"
        else:
            continue
        flags.append({
            "run_date": run_date,
            "app_id": app_id,
            "app_name": app_name,
            "flag_type": "SKEW",
            "severity": severity,
            "detail": (
                f"Stage {s['stage_id']} ({s['stage_name']}): max task duration "
                f"{s['task_duration_max_ms']:.0f}ms is {ratio:.1f}x the median "
                f"({s['task_duration_median_ms']:.0f}ms) across {s['num_tasks']} tasks"
            ),
            "metric_value": ratio,
        })
    return flags


def detect_small_files(stage_metrics: List[dict], app_id: str, app_name: str, run_date: str, cfg: dict) -> List[dict]:
    flags = []
    min_tasks = cfg["min_tasks_to_evaluate"]
    warn_bytes = cfg["avg_bytes_per_task_warning"]
    crit_bytes = cfg["avg_bytes_per_task_critical"]

    for s in stage_metrics:
        if s["num_tasks"] < min_tasks or s["input_bytes"] == 0:
            continue
        avg_bytes = s["avg_bytes_per_task"]
        if avg_bytes <= crit_bytes:
            severity = "CRITICAL"
        elif avg_bytes <= warn_bytes:
            severity = "WARNING"
        else:
            continue
        flags.append({
            "run_date": run_date,
            "app_id": app_id,
            "app_name": app_name,
            "flag_type": "SMALL_FILE",
            "severity": severity,
            "detail": (
                f"Stage {s['stage_id']} ({s['stage_name']}): {s['num_tasks']} tasks averaging "
                f"only {avg_bytes / 1024:.1f} KB input each -- likely small-file / "
                f"over-partitioned input. Consider coalescing upstream output or "
                f"increasing spark.sql.files.maxPartitionBytes."
            ),
            "metric_value": avg_bytes,
        })
    return flags
