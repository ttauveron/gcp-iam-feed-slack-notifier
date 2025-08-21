import logging
import re
from typing import Dict, Any, List

from lib.gcp import crm_client
from lib.logs_url import build_log_url, logs_query_activity
from lib.slack import send_slack_message

IGNORED_ASSET_TYPES = {"storage.googleapis.com/Bucket"}


def _compute_deltas(asset_json: Dict[str, Any]) -> List[Dict[str, Any]]:
    new_bindings = {b["role"]: b for b in asset_json.get("asset", {}).get("iamPolicy", {}).get("bindings", [])}
    old_bindings = {b["role"]: b for b in asset_json.get("priorAsset", {}).get("iamPolicy", {}).get("bindings", [])}

    deltas = []
    for role, new_b in new_bindings.items():
        old_b = old_bindings.get(role)
        new_members = set(new_b.get("members", []))
        old_members = set(old_b.get("members", [])) if old_b else set()
        added_members = sorted(new_members - old_members)

        new_cond = new_b.get("condition")
        old_cond = old_b.get("condition") if old_b else None
        cond_changed = (new_cond or None) != (old_cond or None)

        if added_members or (old_b and cond_changed):
            deltas.append({
                "role": role,
                "members": added_members if added_members else sorted(new_members),
                "condition": new_cond,
                "change": "members_added" if added_members else "condition_changed",
            })
    return deltas


def process_feeds(msg: Dict[str, Any], slack_token: str, channel: str) -> None:
    asset = msg.get("asset") or {}
    asset_type = asset.get("assetType")
    if not asset or not asset_type:
        logging.debug("No asset payload; skip.")
        return
    if asset_type in IGNORED_ASSET_TYPES:
        logging.info("Skipping asset type: %s", asset_type)
        return

    deltas = _compute_deltas(msg)
    if not deltas:
        return

    asset_name = asset.get("name", "unknown")
    ancestors = asset.get("ancestors", []) or []
    ancestor_name = ancestors[0] if ancestors else ""
    update_time = asset.get("updateTime", "")

    resource_type, resource_id, resource_display = "project", "", "Unknown"
    try:
        crm = crm_client()
        if ancestor_name.startswith("projects/"):
            proj = crm.projects().get(name=ancestor_name).execute()
            resource_type = "project"
            resource_id = proj["projectId"]
            resource_display = proj["projectId"]
        elif ancestor_name.startswith("folders/"):
            fld = crm.folders().get(name=ancestor_name).execute()
            resource_type = "folder"
            resource_id = fld.get("name", ancestor_name).split("/")[-1]
            resource_display = f'{fld.get("displayName", ancestor_name)} (*folder-level*)'
        elif ancestor_name.startswith("organizations/"):
            org = crm.organizations().get(name=ancestor_name).execute()
            resource_type = "organization"
            resource_id = org.get("name", ancestor_name).split("/")[-1]
            resource_display = f'{org.get("displayName", ancestor_name)} (*organization-level*)'
        else:
            resource_id = ancestor_name
            resource_display = "Unknown"
    except Exception as e:
        logging.warning("CRM lookup failed (%s). Falling back to raw ancestor.", e)
        resource_id = ancestor_name
        resource_display = "Unknown"

    service_name = re.sub(r"^/*([^/]+)/.*", r"\1", asset_type)
    resource_name = resource_id if "cloudresourcemanager.googleapis.com" in asset_name else asset_name.split("/")[-1]
    query = logs_query_activity(service_name, resource_name)
    scope_key = "organizationId" if resource_type == "organization" else resource_type
    url = build_log_url(query, update_time, scope_key, resource_id)

    lines = [
        f":information_source: New Role Grant in {resource_display}",
        f"*Asset Type:* {asset_type}",
        f"*Asset Name:* {asset_name}",
    ]

    for b in deltas:
        lines.append(f"*Role:* {b['role']}")
        lines.append(f"*Granted to:* {b['members']}")
        if b.get("condition"):
            lines.append(f"*With condition:* {b['condition']}")
        lines.append(f"*<{url}|Browse Audit Logs>*")

    send_slack_message(slack_token, channel, "\n".join(lines))
