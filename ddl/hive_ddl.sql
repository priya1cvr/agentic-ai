CREATE DATABASE IF NOT EXISTS spark_obsv;

CREATE TABLE IF NOT EXISTS spark_obsv.app_metrics (
    app_id             STRING,
    app_name           STRING,
    user               STRING,
    queue              STRING,
    state              STRING,
    final_status       STRING,
    start_time         STRING,
    end_time           STRING,
    duration_sec       DOUBLE,
    allocated_mb       BIGINT,
    allocated_vcores   INT,
    memory_seconds     BIGINT,
    vcore_seconds      BIGINT,
    num_executors      INT,
    executor_memory_mb INT,
    driver_memory_mb   INT,
    executor_cores     INT
)
PARTITIONED BY (run_date STRING)
STORED AS PARQUET;

CREATE TABLE IF NOT EXISTS spark_obsv.executor_metrics (
    app_id                    STRING,
    executor_id               STRING,
    host                      STRING,
    total_cores               INT,
    max_memory_mb             DOUBLE,
    total_tasks               INT,
    total_duration_ms         BIGINT,
    total_gc_time_ms          BIGINT,
    total_input_bytes         BIGINT,
    total_shuffle_read_bytes  BIGINT,
    total_shuffle_write_bytes BIGINT,
    peak_jvm_used_memory_mb   DOUBLE,
    is_active                 BOOLEAN
)
PARTITIONED BY (run_date STRING)
STORED AS PARQUET;

CREATE TABLE IF NOT EXISTS spark_obsv.stage_metrics (
    app_id                   STRING,
    stage_id                 INT,
    stage_name               STRING,
    num_tasks                INT,
    task_duration_min_ms     DOUBLE,
    task_duration_max_ms     DOUBLE,
    task_duration_median_ms  DOUBLE,
    task_duration_p90_ms     DOUBLE,
    skew_ratio               DOUBLE,
    input_bytes               BIGINT,
    shuffle_read_bytes        BIGINT,
    shuffle_write_bytes       BIGINT,
    avg_bytes_per_task        DOUBLE
)
PARTITIONED BY (run_date STRING)
STORED AS PARQUET;

CREATE TABLE IF NOT EXISTS spark_obsv.queue_metrics (
    snapshot_ts        STRING,
    queue_name         STRING,
    capacity_pct       DOUBLE,
    used_capacity_pct  DOUBLE,
    allocated_mb       BIGINT,
    allocated_vcores   INT,
    num_apps_running   INT,
    num_apps_pending   INT
)
PARTITIONED BY (run_date STRING)
STORED AS PARQUET;

CREATE TABLE IF NOT EXISTS spark_obsv.flags (
    app_id        STRING,
    app_name      STRING,
    flag_type     STRING,
    severity      STRING,
    detail        STRING,
    metric_value  DOUBLE
)
PARTITIONED BY (run_date STRING)
STORED AS PARQUET;
