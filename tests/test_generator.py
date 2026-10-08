"""Unit tests for the PDF certificate generator."""

import os
from pathlib import Path

from app.services.certificate_generator import generate_certificate_pdf


def test_pdf_is_created():
    path = generate_certificate_pdf(
        recipient_name="Jane Doe",
        event_name="Intro to Testing",
        event_date="2024-06-01",
        issuer_name="Dr. Smith",
        title="Certificate of Completion",
        job_id=0,
        certificate_id=0,
    )
    assert os.path.isfile(path)
    assert path.endswith(".pdf")


def test_pdf_starts_with_magic_bytes():
    path = generate_certificate_pdf(
        recipient_name="Jane Doe",
        event_name="Intro to Testing",
        event_date="2024-06-01",
        issuer_name="Dr. Smith",
        title="Certificate of Completion",
        job_id=0,
        certificate_id=1,
    )
    with open(path, "rb") as f:
        assert f.read(5) == b"%PDF-"


def test_pdf_has_reasonable_size():
    """A single-page PDF should be between ~1 KB and 500 KB."""
    path = generate_certificate_pdf(
        recipient_name="A B",
        event_name="X",
        event_date="2024-01-01",
        issuer_name="Y",
        title="Certificate",
        job_id=0,
        certificate_id=2,
    )
    size = os.path.getsize(path)
    assert 1_000 < size < 500_000


def test_long_name_does_not_crash():
    """The generator should handle very long names by shrinking the font."""
    path = generate_certificate_pdf(
        recipient_name="A" * 150,
        event_name="Some Really Long Event Name That Might Overflow",
        event_date="2024-12-31",
        issuer_name="Prof. Longname McNameface",
        title="Certificate of Outstanding Achievement in Excellence",
        job_id=0,
        certificate_id=3,
    )
    assert os.path.isfile(path)
