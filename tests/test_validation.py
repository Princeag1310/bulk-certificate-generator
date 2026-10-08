"""Tests for request-payload validation (Pydantic layer)."""

import pytest


def test_missing_event_name(client):
    payload = {
        "issuer_name": "Someone",
        "event_date": "2024-01-01",
        "recipients": [{"name": "A", "email": "a@b.com"}],
    }
    resp = client.post("/api/v1/jobs/", json=payload)
    assert resp.status_code == 422          # Unprocessable Entity


def test_blank_event_name(client):
    payload = {
        "event_name": "   ",
        "issuer_name": "Someone",
        "event_date": "2024-01-01",
        "recipients": [{"name": "A", "email": "a@b.com"}],
    }
    resp = client.post("/api/v1/jobs/", json=payload)
    assert resp.status_code == 422


def test_empty_recipients_list(client):
    payload = {
        "event_name": "Workshop",
        "issuer_name": "Someone",
        "event_date": "2024-01-01",
        "recipients": [],
    }
    resp = client.post("/api/v1/jobs/", json=payload)
    assert resp.status_code == 422
    assert "at least one" in resp.text.lower()


def test_invalid_email(client):
    payload = {
        "event_name": "Workshop",
        "issuer_name": "Someone",
        "event_date": "2024-01-01",
        "recipients": [{"name": "Alice", "email": "not-an-email"}],
    }
    resp = client.post("/api/v1/jobs/", json=payload)
    assert resp.status_code == 422


def test_blank_recipient_name(client):
    payload = {
        "event_name": "Workshop",
        "issuer_name": "Someone",
        "event_date": "2024-01-01",
        "recipients": [{"name": "   ", "email": "a@b.com"}],
    }
    resp = client.post("/api/v1/jobs/", json=payload)
    assert resp.status_code == 422


def test_invalid_date_format(client):
    payload = {
        "event_name": "Workshop",
        "issuer_name": "Someone",
        "event_date": "20-08-2024",        # wrong format
        "recipients": [{"name": "Alice", "email": "a@b.com"}],
    }
    resp = client.post("/api/v1/jobs/", json=payload)
    assert resp.status_code == 422


def test_recipient_name_too_long(client):
    payload = {
        "event_name": "Workshop",
        "issuer_name": "Someone",
        "event_date": "2024-01-01",
        "recipients": [{"name": "A" * 201, "email": "a@b.com"}],
    }
    resp = client.post("/api/v1/jobs/", json=payload)
    assert resp.status_code == 422


def test_valid_minimal_payload(client):
    payload = {
        "event_name": "Workshop",
        "issuer_name": "Someone",
        "event_date": "2024-01-01",
        "recipients": [{"name": "Alice", "email": "a@b.com"}],
    }
    resp = client.post("/api/v1/jobs/", json=payload)
    assert resp.status_code == 201
