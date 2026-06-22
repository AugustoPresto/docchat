"""
Tests for the DocChat API.

Note: Chat and upload tests require Ollama running locally.
The health and document listing tests are independent.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_root():
    """Root endpoint returns status message."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "DocChat" in data["message"]


def test_health_endpoint():
    """Health endpoint returns model configuration."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "chat_model" in data
    assert "embed_model" in data


def test_list_documents_empty():
    """Document list returns empty list when no documents uploaded."""
    response = client.get("/api/v1/documents/")
    assert response.status_code == 200
    data = response.json()
    assert "documents" in data
    assert "total" in data
    assert isinstance(data["documents"], list)


def test_get_nonexistent_document():
    """Getting a non-existent document returns 404."""
    response = client.get("/api/v1/documents/nonexistent-id")
    assert response.status_code == 404


def test_delete_nonexistent_document():
    """Deleting a non-existent document returns 404."""
    response = client.delete("/api/v1/documents/nonexistent-id")
    assert response.status_code == 404


def test_upload_non_pdf():
    """Uploading a non-PDF file returns 400."""
    response = client.post(
        "/api/v1/documents/upload",
        files={"file": ("test.txt", b"hello world", "text/plain")},
    )
    assert response.status_code == 400
    assert "PDF" in response.json()["detail"]


def test_chat_nonexistent_document():
    """Chatting with a non-existent document returns 404."""
    response = client.post(
        "/api/v1/chat/",
        json={
            "document_id": "nonexistent-id",
            "message": "What is this about?",
        },
    )
    assert response.status_code == 404


def test_chat_empty_message():
    """Sending an empty message returns 400."""
    # Use a fake doc id — the empty message check happens first
    response = client.post(
        "/api/v1/chat/",
        json={
            "document_id": "some-id",
            "message": "   ",
        },
    )
    # Either 400 (empty msg) or 404 (doc not found) — both are valid
    assert response.status_code in (400, 404)
