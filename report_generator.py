"""
Daily Health Report
-------------------
Renders a self-contained HTML report summarizing the day's run: totals,
queue allocation, top resource consumers, and every flag raised by the
detectors, grouped by type. Emailed via the same alerting hooks as the DQ
framework, and also written to disk for archival / linking from Grafana.
"""
import os
from datetime import datetime
from typing import List


def _table(rows: List[dict], columns: List[str]) -> str:
    if not rows:
        return "<p><em>None</em></p>"
    head = "".join(f"<th>{c}</th>" for c in columns)
    body = ""
    for r in rows:
        body += "<tr>" + "".join(f"<td>{r.get(c, '')}</td>" for c in columns) + "</tr>"
    return f"<table border='1' cellpadding='6' cellspacing='0'><tr>{head}</tr>{body}</table>"


def generate_html_report(
    run_date: str,
    total_apps: int,
    total_memory_seconds: float,
    total_vcore_seconds: float,
    queue_summary: List[dict],
    flags: List[dict],
    top_offenders: List[dict],
    sla_predictions: List[dict],
    output_dir: str,
) -> str:
    flags_by_type = {}
    for f in flags:
        flags_by_type.setdefault(f["flag_type"], []).append(f)

    sla_risk = [p for p in sla_predictions if p["severity"] in ("WARNING", "CRITICAL")]

    html = f"""
    <html><head><style>
      body {{ font-family: Arial, sans-serif; }}
      h2 {{ border-bottom: 2px solid #444; padding-bottom: 4px; }}
      table {{ border-collapse: collapse; margin-bottom: 20px; }}
      th {{ background: #eee; }}
    </style></head><body>
    <h1>Spark Observability -- Daily Health Report: {run_date}</h1>
    <p>Generated: {datetime.now().isoformat()}</p>

    <h2>Summary</h2>
    <ul>
      <li>Total applications: {total_apps}</li>
      <li>Total memory-seconds consumed: {total_memory_seconds:,.0f}</li>
      <li>Total vcore-seconds consumed: {total_vcore_seconds:,.0f}</li>
      <li>Total flags raised: {len(flags)}</li>
      <li>Apps at SLA risk: {len(sla_risk)}</li>
    </ul>

    <h2>Queue Allocation</h2>
    {_table(queue_summary, ["queue_name", "capacity_pct", "used_capacity_pct", "allocated_mb", "allocated_vcores", "num_apps_running", "num_apps_pending"])}

    <h2>Top Resource Consumers</h2>
    {_table(top_offenders, ["app_name", "queue", "duration_sec", "memory_seconds", "vcore_seconds"])}

    <h2>SLA Risk</h2>
    {_table(sla_risk, ["app_name", "duration_sec", "sla_sec", "breach_probability", "severity", "note"])}

    <h2>Skew Flags</h2>
    {_table(flags_by_type.get("SKEW", []), ["app_name", "severity", "detail", "metric_value"])}

    <h2>Small-File Flags</h2>
    {_table(flags_by_type.get("SMALL_FILE", []), ["app_name", "severity", "detail", "metric_value"])}

    <h2>Underutilization Flags</h2>
    {_table(flags_by_type.get("UNDERUTILIZED", []), ["app_name", "severity", "detail", "metric_value"])}

    </body></html>
    """

    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, f"spark_obsv_report_{run_date}.html")
    with open(path, "w") as f:
        f.write(html)
    return path
