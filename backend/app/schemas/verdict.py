from enum import StrEnum

from pydantic import BaseModel, Field


class Severity(StrEnum):
    INFORMATIONAL = "informational"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Verdict(BaseModel):
    """The structured output of `submit_verdict` — the tool call that ends an investigation."""

    severity: Severity
    mitre_technique: str = Field(description="MITRE ATT&CK technique ID and name, e.g. 'T1110 - Brute Force'")
    summary: str = Field(description="One or two sentence summary of what happened")
    remediation: str = Field(description="Concrete next step(s) for the on-call responder")
    confidence: float = Field(ge=0.0, le=1.0, description="Model's confidence in this verdict")
