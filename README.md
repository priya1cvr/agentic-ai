# Enterprise Spark Observability Framework

## Architecture

```
YARN ResourceManager REST API   Spark History Server REST API
        (apps, queues)             (executors, stages, env)
              \                          /
               \                        /
                v                      v
          YarnCollector          HistoryServerCollector
           (yarn_collector.py)   (history_collector.py, thread-pooled
                                  across ~400-500 apps/day)
                     \                /
                      v              v
                   Metrics normalized into:
                   AppMetric / ExecutorMetric / StageMetric / QueueMetric
                              |
                              v
                       Metrics Store (metrics_store.py)
                       Hive tables (partitioned by run_date)
                       + optional Postgres mirror via JDBC
                              |
              +---------------+----------------+
              |               |                |
              v               v                v
        Skew Detector   Small-File Detector   Underutilization Detector
      (skew_and_small_file_detector.py)      (underutilization_detector.py)
              |               |                |
              +-------+-------+----------------+
                      v
              Trend Analyzer (trend_analyzer.py)
              -- compares today vs trailing 7d/30d avg per app_name
                      |
                      v
              SLA Predictor (sla_predictor.py)
              -- P(breach) from historical mean/stddev vs SLA
                      |
                      v
              Flags written to Hive (spark_obsv.flags)
                      |
                      v
              Daily Health Report (report_generator.py)
              -- self-contained HTML, written to disk
                      |
                      v
              Alerts: Slack / Teams / Email (alerting.py)
                      |
                      v
              Grafana / Tableau (reads the Postgres mirror or Hive tables directly)
```

`cli.py` is the single entry point that wires all of this together and is
what you invoke from the command line / cron / Airflow.

## Files

| File | Purpose |
|---|---|
| `models.py` | Dataclasses for AppMetric, ExecutorMetric, StageMetric, QueueMetric, Flag |
| `yarn_collector.py` | YARN RM REST client: app list + resource-seconds consumed, queue capacity/usage, HA-aware (tries both RMs) |
| `history_collector.py` | Spark History Server REST client: per-executor and per-stage detail, thread-pooled for volume, plus Spark config (executor-memory/cores/instances) from the environment endpoint |
| `metrics_store.py` | Writes all four metric types to Hive (swap to Delta by changing the format string), optional Postgres mirror |
| `skew_and_small_file_detector.py` | Flags stages where max task duration >> median (skew), or many tasks with tiny avg input (small files) |
| `underutilization_detector.py` | Flags apps where allocated CPU-seconds or executor memory was mostly idle |
| `trend_analyzer.py` | Joins today's run against trailing 7d/30d historical averages per `app_name` |
| `sla_predictor.py` | Models each job's duration as Normal(mean, stddev) from 30-day history, computes P(breach) against a configured or default SLA |
| `report_generator.py` | Renders the daily HTML health report |
| `alerting.py` | Slack/Teams summary + emails the full report |
| `cli.py` | Orchestrator / entry point (`--mode collect\|analyze\|report\|all`) |
| `run_observability.sh` | spark-submit wrapper for cron/scheduler |
| `config/observability_config.yaml` | Cluster endpoints, thresholds, SLA overrides, alerting config |
| `ddl/hive_ddl.sql` | DDL for all 5 Hive tables |

## Running it

```bash
# One-shot, all stages, for today:
./run_observability.sh

# Backfill a specific day:
./run_observability.sh 2026-07-15

# Or run stages independently (useful while iterating on detector thresholds):
spark-submit cli.py --config config/observability_config.yaml --mode collect --run-date 2026-07-17
spark-submit cli.py --config config/observability_config.yaml --mode analyze --run-date 2026-07-17
spark-submit cli.py --config config/observability_config.yaml --mode report  --run-date 2026-07-17
```

## Design notes / things to tune for your cluster

- **Volume (400-500 apps/day):** `history_collector.py` fans out per-app
  executor+stage calls across a `ThreadPoolExecutor`
  (`collection.max_parallel_requests` in config, default 20). Raise/lower
  based on how much load your History Server can take.
- **YARN HA:** `yarn_collector.py` tries the last-known-active RM first,
  falls back to the others in `cluster.yarn_rm_urls` on failure.
- **Kerberized clusters:** set `cluster.kerberos_enabled: true`; requires
  `requests-kerberos` installed on the driver node.
- **Skew ratio** (`max_task_duration / median_task_duration`) and
  **small-file threshold** (avg bytes/task) are both configurable per-cluster
  in `thresholds.skew` / `thresholds.small_file` — the shipped defaults
  (3x/8x skew, 10MB/1MB small-file) are reasonable starting points, not gospel.
- **SLA prediction** currently uses only the historical mean (stddev defaults
  to 15% of the mean when not computed). To get real stddev, extend
  `trend_analyzer.build_trend_comparison` with a `STDDEV(duration_sec)`
  aggregate and pass it through in `cli.py`'s `do_analyze`.
- **Grafana:** point it at the Postgres mirror (`jdbc.*` in config) rather
  than Hive directly — most Grafana deployments don't have a performant Hive
  data source plugin. Tableau can go either route (Hive ODBC or Postgres).
- **Delta instead of Hive-on-Parquet:** change `format("parquet")` to
  `format("delta")` in `metrics_store.py`'s `saveAsTable` call; everything
  else (schema, partitioning, queries) stays the same.

## Extending

- New detector: write a `detect_x(...)` function returning `Flag`-shaped
  dicts, call it from `do_analyze()` in `cli.py`.
- New metric source (e.g. Spark `/api/v1/applications/{id}/jobs` for
  job-level detail): add a collector method + a model + a store table,
  following the existing executor/stage pattern.
