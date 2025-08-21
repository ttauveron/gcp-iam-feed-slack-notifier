import urllib.parse


def build_log_url(query: str, around_rfc3339: str, scope_key: str, scope_value: str) -> str:
    q_enc = urllib.parse.quote(query, safe="")
    # Semicolon-delimited parameters (no "?")
    return (
        "https://console.cloud.google.com/logs/query;"
        f"query={q_enc};aroundTime={around_rfc3339};duration=PT2M;"
        f"{scope_key}={scope_value}"
    )


def logs_query_activity(service_name: str, resource_name: str) -> str:
    return (
        'log_id("cloudaudit.googleapis.com/activity")\n'
        f'protoPayload.serviceName="{service_name}"\n'
        f'protoPayload.resourceName:"{resource_name}"'
    )


def logs_query_bucket_adds(bucket_name: str) -> str:
    return (
        'log_id("cloudaudit.googleapis.com/activity")\n'
        'protoPayload.serviceName="storage.googleapis.com"\n'
        'protoPayload.methodName="storage.setIamPermissions"\n'
        f'protoPayload.resourceName="projects/_/buckets/{bucket_name}"\n'
        'protoPayload.serviceData.policyDelta.bindingDeltas.action="ADD"'
    )
