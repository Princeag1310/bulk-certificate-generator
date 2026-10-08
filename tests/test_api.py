"""Integration tests for the /api/v1/jobs endpoints."""

from unittest.mock import patch


# ── job creation ────────────────────────────────────────────────────────────

def test_create_job_returns_201(client, sample_payload):
    resp = client.post("/api/v1/jobs/", json=sample_payload)
    assert resp.status_code == 201


def test_create_job_response_fields(client, sample_payload):
    data = client.post("/api/v1/jobs/", json=sample_payload).json()

    assert data["event_name"] == "Advanced Python Workshop"
    assert data["total_recipients"] == 3
    assert "id" in data
    assert "created_at" in data


def test_job_completes_after_creation(client, sample_payload):
    """Background tasks run synchronously inside TestClient."""
    job_id = client.post("/api/v1/jobs/", json=sample_payload).json()["id"]
    detail = client.get(f"/api/v1/jobs/{job_id}").json()

    assert detail["status"] == "completed"
    assert detail["successful_count"] == 3
    assert detail["failed_count"] == 0


# ── listing / detail ───────────────────────────────────────────────────────

def test_list_jobs(client, sample_payload):
    client.post("/api/v1/jobs/", json=sample_payload)
    jobs = client.get("/api/v1/jobs/").json()

    assert isinstance(jobs, list)
    assert len(jobs) >= 1


def test_get_job_not_found(client):
    assert client.get("/api/v1/jobs/9999").status_code == 404


def test_get_job_detail_includes_certificates(client, sample_payload):
    job_id = client.post("/api/v1/jobs/", json=sample_payload).json()["id"]
    detail = client.get(f"/api/v1/jobs/{job_id}").json()

    assert len(detail["certificates"]) == 3
    names = {c["recipient_name"] for c in detail["certificates"]}
    assert names == {"Alice Johnson", "Bob Williams", "Charlie Brown"}


def test_list_certificates_endpoint(client, sample_payload):
    job_id = client.post("/api/v1/jobs/", json=sample_payload).json()["id"]
    certs = client.get(f"/api/v1/jobs/{job_id}/certificates").json()

    assert len(certs) == 3


# ── downloads ───────────────────────────────────────────────────────────────

def test_download_single_certificate(client, sample_payload):
    job_id = client.post("/api/v1/jobs/", json=sample_payload).json()["id"]
    detail = client.get(f"/api/v1/jobs/{job_id}").json()

    cert_id = detail["certificates"][0]["id"]
    dl = client.get(f"/api/v1/jobs/{job_id}/certificates/{cert_id}/download")

    assert dl.status_code == 200
    assert dl.headers["content-type"] == "application/pdf"
    assert dl.content[:5] == b"%PDF-"


def test_download_missing_certificate(client, sample_payload):
    job_id = client.post("/api/v1/jobs/", json=sample_payload).json()["id"]
    resp = client.get(f"/api/v1/jobs/{job_id}/certificates/9999/download")

    assert resp.status_code == 404


def test_download_all_as_zip(client, sample_payload):
    job_id = client.post("/api/v1/jobs/", json=sample_payload).json()["id"]
    dl = client.get(f"/api/v1/jobs/{job_id}/download")

    assert dl.status_code == 200
    assert "zip" in dl.headers["content-type"]
    # ZIP magic bytes
    assert dl.content[:2] == b"PK"


# ── partial-failure handling ────────────────────────────────────────────────

def test_partial_failure_does_not_block_others(client):
    """
    Mock the PDF generator so it raises for one recipient.
    The other two should still succeed and the job should be
    marked 'completed_with_errors'.
    """
    from app.services.certificate_generator import (
        generate_certificate_pdf as real_gen,
    )

    def _flaky_gen(**kwargs):
        if kwargs["recipient_name"] == "Bob Williams":
            raise RuntimeError("Simulated rendering failure")
        return real_gen(**kwargs)

    payload = {
        "title": "Test Cert",
        "event_name": "Workshop",
        "event_date": "2024-01-01",
        "issuer_name": "Tester",
        "recipients": [
            {"name": "Alice Johnson", "email": "a@example.com"},
            {"name": "Bob Williams", "email": "b@example.com"},
            {"name": "Charlie Brown", "email": "c@example.com"},
        ],
    }

    with patch(
        "app.services.job_processor.generate_certificate_pdf",
        side_effect=_flaky_gen,
    ):
        job_id = client.post("/api/v1/jobs/", json=payload).json()["id"]

    detail = client.get(f"/api/v1/jobs/{job_id}").json()

    assert detail["status"] == "completed_with_errors"
    assert detail["successful_count"] == 2
    assert detail["failed_count"] == 1

    statuses = {c["recipient_name"]: c["status"] for c in detail["certificates"]}
    assert statuses["Alice Johnson"] == "completed"
    assert statuses["Bob Williams"] == "failed"
    assert statuses["Charlie Brown"] == "completed"

    # the failed certificate should carry an error message
    bob = next(c for c in detail["certificates"] if c["recipient_name"] == "Bob Williams")
    assert bob["error_message"] is not None


# ── health check ────────────────────────────────────────────────────────────

def test_health(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"
