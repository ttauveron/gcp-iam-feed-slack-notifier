import logging
import re
from typing import Any, Dict

from lib.logs_url import build_log_url, logs_query_bucket_adds
from lib.slack import send_slack_message


def process_audit_logs(msg: Dict[str, Any], slack_token: str, channel: str) -> None:
    """GCS Admin Activity audit log handler — includes raw condition dicts like asset feed."""
    pp = msg.get("protoPayload", {}) or {}
    res = msg.get("resource", {}) or {}
    labels = res.get("labels", {}) or {}

    if not (
            pp.get("serviceName") == "storage.googleapis.com"
            and pp.get("methodName") == "storage.setIamPermissions"
            and res.get("type") == "gcs_bucket"
    ):
        logging.debug("Not a GCS SetIamPolicy event.")
        return

    # Keep only ADD binding deltas
    deltas = (pp.get("serviceData", {}).get("policyDelta", {}).get("bindingDeltas", []) or [])
    adds = [d for d in deltas if d.get("action") == "ADD"]
    if not adds:
        logging.info("Bucket IAM change has no ADD actions; skipping notify.")
        return

    # Resource details
    bucket = labels.get("bucket_name")
    if not bucket:
        rn = pp.get("resourceName", "")
        m = re.search(r"/buckets/([^/]+)$", rn)
        bucket = m.group(1) if m else rn or "unknown-bucket"

    project_id = labels.get("project_id", "unknown-project")
    actor = pp.get("authenticationInfo", {}).get("principalEmail", "unknown")
    ts = msg.get("timestamp") or ""

    url = build_log_url(logs_query_bucket_adds(bucket), ts, "project", project_id)

    # Compose Slack message
    lines = [
        f":information_source: New Role Grant in `{project_id}`",
        "*Asset Type:* storage.googleapis.com/Bucket",
        f"*Bucket:* {bucket}",
        f"*Actor:* {actor}",
    ]

    for d in adds:
        role = d.get("role", "unknown-role")
        member = d.get("member", "unknown-member")
        lines.append(f"*Role:* {role}")
        lines.append(f"*Granted to:* [{member}]")
        if d.get("condition"):
            lines.append(f"*With condition:* {d['condition']}")
        lines.append(f"*<{url}|Browse Audit Logs>*")

    send_slack_message(slack_token, channel, "\n".join(lines))
