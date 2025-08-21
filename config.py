import os
import logging
from dataclasses import dataclass

DEFAULT_CHANNEL = "#test-temp"

@dataclass(frozen=True)
class Config:
    slack_token: str
    slack_channel: str
    log_level: int

def load_config() -> Config:
    log_level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, log_level_name, logging.INFO)

    token = os.getenv("SLACK_TOKEN", "")
    channel = os.getenv("SLACK_CHANNEL", DEFAULT_CHANNEL)

    return Config(slack_token=token, slack_channel=channel, log_level=level)
