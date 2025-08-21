import logging
import re
from collections import defaultdict
from typing import Dict, Any

from lib.logs_url import build_log_url, logs_query_bucket_adds
from lib.slack import send_slack_message


def process_audit_logs(msg: Dict[str, Any], slack_token: str, channel: str) -> None:
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

    deltas = (
            pp.get("serviceData", {}).get("policyDelta", {}).get("bindingDeltas", []) or []
    )
    adds = [d for d in deltas if d.get("action") == "ADD"]
    if not adds:
        logging.info("Bucket IAM change has no ADD actions; skipping notify.")
        return

    bucket = labels.get("bucket_name")
    if not bucket:
        rn = pp.get("resourceName", "")
        m = re.search(r"/buckets/([^/]+)$", rn)
        bucket = m.group(1) if m else rn or "unknown-bucket"

    project_id = labels.get("project_id", "unknown-project")
    actor = pp.get("authenticationInfo", {}).get("principalEmail", "unknown")
    ts = msg.get("timestamp") or ""

    role_to_members = defaultdict(list)
    for d in adds:
        role_to_members[d.get("role", "unknown-role")].append(d.get("member", "unknown-member"))

    query = logs_query_bucket_adds(bucket)
    url = build_log_url(query, ts, "project", project_id)

    lines = [
        f":information_source: New Role Grant in `{project_id}`",
        "*Asset Type:* storage.googleapis.com/Bucket",
        f"*Bucket:* {bucket}",
        f"*Actor:* {actor}",
    ]
    for role, members in sorted(role_to_members.items()):
        lines.append(f"*Role:* {role}")
        lines.append(f"*Granted to:* {sorted(set(members))}")
        lines.append(f"*<{url}|Browse Audit Logs>*")

    send_slack_message(slack_token, channel, "\n".join(lines))
