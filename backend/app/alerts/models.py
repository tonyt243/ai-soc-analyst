from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class AlertType(StrEnum):
    SSH_BRUTE_FORCE = "ssh_brute_force"
    LOG4SHELL = "log4shell"
    PORT_SCAN = "port_scan"
    DATA_EXFILTRATION = "data_exfiltration"
    SUSPICIOUS_POWERSHELL = "suspicious_powershell"


class Alert(BaseModel):
    """A synthetic alert. `raw_log` is what gets handed to the agent as its starting evidence."""

    id: str
    type: AlertType
    title: str
    source_ip: str
    raw_log: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)
