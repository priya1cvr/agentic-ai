"""
Core data models for the Spark Observability Framework.
Dependency-free dataclasses -- easy to serialize into Spark Rows for the
metrics store, and easy to unit test independent of any live cluster.
"""
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class AppMetric:
    run_date: str
    app_id: str
    app_name: str
    user: str
    queue: str
    state: str                 # RUNNING / FINISHED / FAILED / KILLED
    final_status: str          # UNDEFINED / SUCCEEDED / FAILED / KILLED
    start_time: str            # ISO timestamp
    end_time: Optional[str]
    duration_sec: float
    allocated_mb: int          # memorySeconds-derived avg allocated MB (YARN)
    allocated_vcores: int
    memory_seconds: int        # YARN resource: MB-seconds consumed
    vcore_seconds: int
    num_executors: int
    executor_memory_mb: int
    driver_memory_mb: int
    executor_cores: int


@dataclass
class ExecutorMetric:
    run_date: str
    app_id: str
    executor_id: str
    host: str
    total_cores: int
    max_memory_mb: int
    total_tasks: int
    total_duration_ms: int
    total_gc_time_ms: int
    total_input_bytes: int
    total_shuffle_read_bytes: int
    total_shuffle_write_bytes: int
    peak_jvm_used_memory_mb: float
    is_active: bool


@dataclass
class StageMetric:
    run_date: str
    app_id: str
    stage_id: int
    stage_name: str
    num_tasks: int
    task_duration_min_ms: float
    task_duration_max_ms: float
    task_duration_median_ms: float
    task_duration_p90_ms: float
    skew_ratio: float          # max / median task duration
    input_bytes: int
    shuffle_read_bytes: int
    shuffle_write_bytes: int
    avg_bytes_per_task: float


@dataclass
class QueueMetric:
    run_date: str
    snapshot_ts: str
    queue_name: str
    capacity_pct: float
    used_capacity_pct: float
    allocated_mb: int
    allocated_vcores: int
    num_apps_running: int
    num_apps_pending: int


@dataclass
class Flag:
    run_date: str
    app_id: str
    app_name: str
    flag_type: str             # SKEW | SMALL_FILE | UNDERUTILIZED | SLA_RISK
    severity: str               # CRITICAL | WARNING | INFO
    detail: str
    metric_value: float
