from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, field_validator

from app.models import JobStatus, CertificateStatus
from app.config import MAX_RECIPIENTS_PER_JOB


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class RecipientIn(BaseModel):
    name: str
    email: EmailStr

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Recipient name cannot be empty")
        if len(v) > 200:
            raise ValueError("Recipient name must be 200 characters or fewer")
        return v


class JobCreateRequest(BaseModel):
    title: str = "Certificate of Completion"
    event_name: str
    event_date: date
    issuer_name: str
    recipients: list[RecipientIn]

    @field_validator("event_name")
    @classmethod
    def event_name_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Event name cannot be empty")
        return v

    @field_validator("issuer_name")
    @classmethod
    def issuer_name_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Issuer name cannot be empty")
        return v

    @field_validator("recipients")
    @classmethod
    def recipients_limits(cls, v: list[RecipientIn]) -> list[RecipientIn]:
        if len(v) == 0:
            raise ValueError("At least one recipient is required")
        if len(v) > MAX_RECIPIENTS_PER_JOB:
            raise ValueError(
                f"A single request can contain at most {MAX_RECIPIENTS_PER_JOB} recipients"
            )
        return v


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class CertificateOut(BaseModel):
    id: int
    job_id: int
    recipient_name: str
    recipient_email: str
    status: CertificateStatus
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class JobOut(BaseModel):
    id: int
    title: str
    event_name: str
    event_date: str
    issuer_name: str
    status: JobStatus
    total_recipients: int
    successful_count: int
    failed_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class JobDetailOut(JobOut):
    """Job info plus the list of individual certificates."""
    certificates: list[CertificateOut] = []
