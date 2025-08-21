import logging
import time
from typing import Tuple

import requests


def send_slack_message(token: str, channel: str, text: str) -> Tuple[str, int]:
    if not token:
        logging.error("SLACK_TOKEN missing.")
        return "Missing SLACK_TOKEN", 500

    payload = {
        "channel": channel,
        "text": text,
        "username": "IAM Notification",
        "unfurl_links": False,
        "unfurl_media": False,
        "icon_emoji": ":identification_card:",
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }

    for attempt in range(3):
        try:
            resp = requests.post(
                "https://slack.com/api/chat.postMessage",
                json=payload,
                headers=headers,
                timeout=(3, 10),
            )
        except requests.RequestException as e:
            logging.warning("Slack request error: %s", e)
            if attempt == 2:
                return (f"Failure: {e}", 500)
            time.sleep(2 ** attempt)
            continue

        if resp.status_code == 200 and resp.json().get("ok", False):
            return ("Success", 200)

        if resp.status_code in (429, 500, 502, 503, 504):
            retry_after = int(resp.headers.get("Retry-After", "0"))
            sleep_for = max(retry_after, 2 ** attempt)
            time.sleep(sleep_for)
            continue

        return (f"Failure: {resp.text}", 500)

    return ("Failure after retries", 500)
