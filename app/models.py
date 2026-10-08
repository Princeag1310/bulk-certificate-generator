import enum
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class JobStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    COMPLETED_WITH_ERRORS = "completed_with_errors"
    FAILED = "failed"


class CertificateStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class Job(Base):
    """Represents a single bulk-generation request."""

    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    event_name = Column(String(255), nullable=False)
    event_date = Column(String(50), nullable=False)      # stored as ISO string
    issuer_name = Column(String(255), nullable=False)

    status = Column(Enum(JobStatus), default=JobStatus.PENDING, nullable=False)
    total_recipients = Column(Integer, default=0)
    successful_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)

    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    certificates = relationship(
        "Certificate", back_populates="job", cascade="all, delete-orphan"
    )


class Certificate(Base):
    """One generated (or failed) certificate inside a job."""

    __tablename__ = "certificates"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)

    recipient_name = Column(String(255), nullable=False)
    recipient_email = Column(String(255), nullable=False)

    status = Column(
        Enum(CertificateStatus), default=CertificateStatus.PENDING, nullable=False
    )
    error_message = Column(Text, nullable=True)
    file_path = Column(String(512), nullable=True)

    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    job = relationship("Job", back_populates="certificates")
