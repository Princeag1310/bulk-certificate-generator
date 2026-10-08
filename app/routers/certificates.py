import io
import zipfile
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Job, Certificate, JobStatus, CertificateStatus
from app.schemas import JobCreateRequest, JobOut, JobDetailOut, CertificateOut
from app.services.job_processor import process_job

router = APIRouter(prefix="/api/v1/jobs", tags=["Jobs"])


# ── create ──────────────────────────────────────────────────────────────────

@router.post("/", response_model=JobOut, status_code=201)
def create_job(
    request: JobCreateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Submit a bulk certificate-generation request.

    The response returns immediately with the job metadata.
    Actual PDF generation happens in the background.
    """
    job = Job(
        title=request.title,
        event_name=request.event_name,
        event_date=str(request.event_date),
        issuer_name=request.issuer_name,
        status=JobStatus.PENDING,
        total_recipients=len(request.recipients),
    )
    db.add(job)
    db.flush()                                   # assigns job.id

    for r in request.recipients:
        db.add(
            Certificate(
                job_id=job.id,
                recipient_name=r.name,
                recipient_email=r.email,
                status=CertificateStatus.PENDING,
            )
        )

    db.commit()
    db.refresh(job)

    background_tasks.add_task(process_job, job.id)

    return job


# ── list / detail ───────────────────────────────────────────────────────────

@router.get("/", response_model=list[JobOut])
def list_jobs(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    """Return a paginated list of jobs (newest first)."""
    return (
        db.query(Job)
        .order_by(Job.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.get("/{job_id}", response_model=JobDetailOut)
def get_job(job_id: int, db: Session = Depends(get_db)):
    """Full job details including every certificate's status."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/{job_id}/certificates", response_model=list[CertificateOut])
def list_certificates(job_id: int, db: Session = Depends(get_db)):
    """List certificates that belong to a job."""
    if not db.query(Job).filter(Job.id == job_id).first():
        raise HTTPException(status_code=404, detail="Job not found")
    return (
        db.query(Certificate)
        .filter(Certificate.job_id == job_id)
        .all()
    )


# ── downloads ───────────────────────────────────────────────────────────────

@router.get("/{job_id}/certificates/{certificate_id}/download")
def download_certificate(
    job_id: int,
    certificate_id: int,
    db: Session = Depends(get_db),
):
    """Download a single certificate PDF."""
    cert = (
        db.query(Certificate)
        .filter(Certificate.id == certificate_id, Certificate.job_id == job_id)
        .first()
    )
    if not cert:
        raise HTTPException(status_code=404, detail="Certificate not found")

    if cert.status != CertificateStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail=f"Certificate not ready (status: {cert.status.value})",
        )

    if not cert.file_path or not Path(cert.file_path).exists():
        raise HTTPException(status_code=404, detail="Certificate file missing on disk")

    safe_name = cert.recipient_name.replace(" ", "_")
    return FileResponse(
        path=cert.file_path,
        media_type="application/pdf",
        filename=f"certificate_{safe_name}.pdf",
    )


@router.get("/{job_id}/download")
def download_all_certificates(job_id: int, db: Session = Depends(get_db)):
    """
    Download every *completed* certificate for a job as a single ZIP file.
    Returns 400 if the job is still running.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status in (JobStatus.PENDING, JobStatus.PROCESSING):
        raise HTTPException(status_code=400, detail="Job is still being processed")

    completed = (
        db.query(Certificate)
        .filter(
            Certificate.job_id == job_id,
            Certificate.status == CertificateStatus.COMPLETED,
        )
        .all()
    )
    if not completed:
        raise HTTPException(status_code=404, detail="No completed certificates to download")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for cert in completed:
            if cert.file_path and Path(cert.file_path).exists():
                arcname = f"certificate_{cert.recipient_name.replace(' ', '_')}_{cert.id}.pdf"
                zf.write(cert.file_path, arcname)
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename=job_{job_id}_certificates.zip"
        },
    )
