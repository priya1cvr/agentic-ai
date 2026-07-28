"""
Alerting
--------
Posts a condensed summary to Slack/Teams, and emails the full HTML report
as an attachment to the platform team. Mirrors the DQ framework's alerting
module so on-call folks see a consistent format across both systems.
"""
import json
import smtplib
import urllib.request
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def post_summary(slack_webhook, teams_webhook, run_date, total_apps, flags, sla_risk):
    if not (slack_webhook or teams_webhook):
        return
    crit = sum(1 for f in flags if f["severity"] == "CRITICAL")
    warn = sum(1 for f in flags if f["severity"] == "WARNING")
    message = (
        f"*Spark Observability -- {run_date}*\n"
        f"{total_apps} apps analyzed | {crit} critical flags | {warn} warnings | "
        f"{len(sla_risk)} apps at SLA risk"
    )
    payload = json.dumps({"text": message}).encode("utf-8")
    for url in filter(None, [slack_webhook, teams_webhook]):
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=10)


def email_report(smtp_cfg, run_date, report_path):
    if not smtp_cfg:
        return
    msg = MIMEMultipart()
    msg["Subject"] = f"Spark Observability Daily Report -- {run_date}"
    msg["From"] = smtp_cfg["from_addr"]
    msg["To"] = ", ".join(smtp_cfg["to_addrs"])
    msg.attach(MIMEText(f"Daily Spark observability report for {run_date} attached.", "plain"))

    with open(report_path, "rb") as f:
        part = MIMEApplication(f.read(), _subtype="html")
        part.add_header("Content-Disposition", "attachment", filename=f"spark_obsv_report_{run_date}.html")
        msg.attach(part)

    with smtplib.SMTP(smtp_cfg["host"], smtp_cfg.get("port", 25)) as server:
        server.sendmail(msg["From"], smtp_cfg["to_addrs"], msg.as_string())
