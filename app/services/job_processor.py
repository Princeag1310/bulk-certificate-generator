"""
Background job processor.

`process_job` is designed to be called via FastAPI's BackgroundTasks.
It fans the actual PDF generation out to a ThreadPoolExecutor so that
multiple certificates are rendered in parallel, while all DB writes
happen sequentially on the background-task thread (SQLite-friendly).
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from sqlalchemy.orm import Session

from app.config import MAX_WORKERS
from app.database import SessionLocal
from app.models import Job, Certificate, JobStatus, CertificateStatus
from app.services.certificate_generator import generate_certificate_pdf

logger = logging.getLogger(__name__)


def _render_one(
    certificate_id: int,
    recipient_name: str,
    event_name: str,
    event_date: str,
    issuer_name: str,
    title: str,
    job_id: int,
) -> tuple[int, bool, str | None, str | None]:
    """
    Pure computation – no DB access.
    Returns (certificate_id, success, file_path | None, error_msg | None).
    """
    try:
        path = generate_certificate_pdf(
            recipient_name=recipient_name,
            event_name=event_name,
            event_date=event_date,
            issuer_name=issuer_name,
            title=title,
            job_id=job_id,
            certificate_id=certificate_id,
        )
        return (certificate_id, True, path, None)
    except Exception as exc:
        logger.error("Certificate %s failed: %s", certificate_id, exc)
        return (certificate_id, False, None, str(exc))


def process_job(job_id: int) -> None:
    """
    Fetch pending certificates for *job_id*, generate PDFs in parallel,
    and update statuses.  Meant to run in a background thread.
    """
    db: Session = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if job is None:
            logger.error("Job %s not found – nothing to process", job_id)
            return

        job.status = JobStatus.PROCESSING
        db.commit()

        certificates = (
            db.query(Certificate)
            .filter(Certificate.job_id == job_id)
            .all()
        )

        # build task kwargs for the executor
        tasks = [
            dict(
                certificate_id=cert.id,
                recipient_name=cert.recipient_name,
                event_name=job.event_name,
                event_date=job.event_date,
                issuer_name=job.issuer_name,
                title=job.title,
                job_id=job.id,
            )
            for cert in certificates
        ]

        ok = 0
        fail = 0

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            futures = {
                pool.submit(_render_one, **t): t["certificate_id"]
                for t in tasks
            }

            for future in as_completed(futures):
                cid, success, fpath, errmsg = future.result()

                cert = (
                    db.query(Certificate)
                    .filter(Certificate.id == cid)
                    .first()
                )
                if cert is None:
                    continue

                if success:
                    cert.status = CertificateStatus.COMPLETED
                    cert.file_path = fpath
                    ok += 1
                else:
                    cert.status = CertificateStatus.FAILED
                    cert.error_message = errmsg
                    fail += 1

                db.commit()          # commit after each so progress is visible

        # final job-level update
        job = db.query(Job).filter(Job.id == job_id).first()
        job.successful_count = ok
        job.failed_count = fail

        if fail == 0:
            job.status = JobStatus.COMPLETED
        elif ok == 0:
            job.status = JobStatus.FAILED
        else:
            job.status = JobStatus.COMPLETED_WITH_ERRORS

        db.commit()
        logger.info(
            "Job %s done – %d succeeded, %d failed", job_id, ok, fail
        )

    except Exception as exc:
        logger.exception("Job %s crashed: %s", job_id, exc)
        try:
            job = db.query(Job).filter(Job.id == job_id).first()
            if job:
                job.status = JobStatus.FAILED
                db.commit()
        except Exception:
            pass
    finally:
        db.close()
