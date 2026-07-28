"""
Executor Underutilization Detector
------------------------------------
Flags apps where allocated executor resources (memory, CPU-seconds) were
mostly idle -- the classic "over-provisioned Spark job" pattern that wastes
queue capacity other jobs could have used.

Two independent signals, either one can flag:
  - CPU:    sum(executor task run-time) / (allocated vcore-seconds) is low
            -> executors were sitting idle rather than computing.
  - Memory: peak JVM heap used / max configured executor memory is low
            -> executor-memory is oversized for what the job actually needs.
"""
from typing import List


def detect_underutilization(
    app_metric: dict,
    executor_metrics: List[dict],
    run_date: str,
    cfg: dict,
) -> List[dict]:
    flags = []
    if app_metric["duration_sec"] < cfg["min_duration_sec"] or not executor_metrics:
        return flags

    total_task_time_sec = sum(e["total_duration_ms"] for e in executor_metrics) / 1000.0
    allocated_core_seconds = app_metric["vcore_seconds"] or 1
    cpu_ratio = total_task_time_sec / allocated_core_seconds

    max_mem_mb = max((e["max_memory_mb"] for e in executor_metrics), default=0) or 1
    peak_mem_mb = max((e["peak_jvm_used_memory_mb"] for e in executor_metrics), default=0)
    mem_ratio = peak_mem_mb / max_mem_mb

    if cpu_ratio < cfg["cpu_time_ratio_warning"]:
        flags.append({
            "run_date": run_date,
            "app_id": app_metric["app_id"],
            "app_name": app_metric["app_name"],
            "flag_type": "UNDERUTILIZED",
            "severity": "WARNING",
            "detail": (
                f"CPU utilization {cpu_ratio * 100:.1f}% -- {total_task_time_sec:.0f}s of actual "
                f"task compute out of {allocated_core_seconds:.0f} allocated vcore-seconds. "
                f"Consider reducing num-executors or executor-cores."
            ),
            "metric_value": round(cpu_ratio, 4),
        })

    if mem_ratio < cfg["memory_ratio_warning"]:
        flags.append({
            "run_date": run_date,
            "app_id": app_metric["app_id"],
            "app_name": app_metric["app_name"],
            "flag_type": "UNDERUTILIZED",
            "severity": "WARNING",
            "detail": (
                f"Memory utilization {mem_ratio * 100:.1f}% -- peak JVM heap used "
                f"{peak_mem_mb:.0f}MB out of {max_mem_mb:.0f}MB configured executor memory. "
                f"Consider reducing executor-memory."
            ),
            "metric_value": round(mem_ratio, 4),
        })

    return flags
