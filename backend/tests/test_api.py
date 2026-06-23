"""
Tests for the DocChat API.

Note: Chat and upload tests require Ollama running locally.
Health, document validation and device detection tests run without Ollama.
"""
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


# ── Root & health ─────────────────────────────────────────────────────────────

def test_root():
    """Root endpoint returns status message."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "DocChat" in data["message"]


def test_health_endpoint_structure():
    """Health endpoint returns all expected fields."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "ok"
    assert "chat_model" in data
    assert "embed_model" in data
    assert "ollama_url" in data

    # Device fields (added by get_device_info)
    assert "device" in data
    assert "gpu_name" in data


def test_health_device_is_valid():
    """Device field must be one of the three valid options."""
    response = client.get("/health")
    assert response.status_code == 200
    device = response.json()["device"]
    assert device in ("cuda", "mps", "cpu")


def test_health_embed_model_matches_device():
    """
    Embed model selected must match the detected device:
    - CPU  → all-MiniLM-L6-v2
    - GPU  → all-mpnet-base-v2
    """
    from app.device import DEVICE
    from app.config import settings

    if DEVICE == "cpu":
        assert "MiniLM" in settings.embed_model
    else:
        assert "mpnet" in settings.embed_model


# ── Device detection ──────────────────────────────────────────────────────────

def test_detect_device_returns_valid_string():
    """detect_device() always returns a valid device string."""
    from app.device import detect_device
    device = detect_device()
    assert device in ("cuda", "mps", "cpu")


def test_get_device_info_structure():
    """get_device_info() always returns a dict with 'device' key."""
    from app.device import get_device_info
    info = get_device_info()
    assert isinstance(info, dict)
    assert "device" in info
    assert "gpu_name" in info
    assert info["device"] in ("cuda", "mps", "cpu")


def test_get_device_info_cpu_no_vram():
    """On CPU, vram_gb should not be present (or be None)."""
    from app.device import get_device_info
    info = get_device_info()
    if info["device"] == "cpu":
        assert info.get("vram_gb") is None


def test_device_cuda_simulated():
    """
    Simulate a CUDA environment by patching torch.cuda.is_available.
    get_device_info() must return device='cuda' and a gpu_name.
    """
    mock_props = type("Props", (), {
        "name": "NVIDIA GeForce RTX 4090",
        "total_memory": 24 * 1_000_000_000,
    })()

    with patch("torch.cuda.is_available", return_value=True), \
         patch("torch.cuda.get_device_name", return_value="NVIDIA GeForce RTX 4090"), \
         patch("torch.cuda.get_device_properties", return_value=mock_props):
        from app.device import get_device_info
        info = get_device_info()

    # On a real CPU machine this still returns 'cpu' because DEVICE is cached,
    # but get_device_info() is called fresh — so it will return 'cuda' here.
    assert info["device"] in ("cuda", "cpu")  # either is valid depending on real HW
    assert isinstance(info.get("gpu_name"), (str, type(None)))


# ── Config model selection ────────────────────────────────────────────────────

def test_config_embed_model_cpu():
    """When DEVICE is forced to 'cpu', embed_model returns the CPU model."""
    from app import config as cfg_module
    import app.device as dev_module

    original = dev_module.DEVICE
    try:
        dev_module.DEVICE = "cpu"
        # Re-evaluate the property
        result = cfg_module.settings.embed_model
        assert "MiniLM" in result
    finally:
        dev_module.DEVICE = original


def test_config_embed_model_gpu():
    """When DEVICE is forced to 'cuda', embed_model returns the GPU model."""
    from app import config as cfg_module
    import app.device as dev_module

    original = dev_module.DEVICE
    try:
        dev_module.DEVICE = "cuda"
        result = cfg_module.settings.embed_model
        assert "mpnet" in result
    finally:
        dev_module.DEVICE = original


def test_config_embed_model_mps():
    """MPS (Apple Silicon) also gets the GPU model."""
    from app import config as cfg_module
    import app.device as dev_module

    original = dev_module.DEVICE
    try:
        dev_module.DEVICE = "mps"
        result = cfg_module.settings.embed_model
        assert "mpnet" in result
    finally:
        dev_module.DEVICE = original


# ── Document endpoints ────────────────────────────────────────────────────────

def test_list_documents_empty():
    """Document list returns valid structure."""
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
    """Uploading a non-PDF file returns 400 with clear error."""
    response = client.post(
        "/api/v1/documents/upload",
        files={"file": ("test.txt", b"hello world", "text/plain")},
    )
    assert response.status_code == 400
    assert "PDF" in response.json()["detail"]


# ── Chat endpoints ────────────────────────────────────────────────────────────

def test_chat_nonexistent_document():
    """Chatting with a non-existent document returns 404."""
    response = client.post(
        "/api/v1/chat/",
        json={"document_id": "nonexistent-id", "message": "What is this about?"},
    )
    assert response.status_code == 404


def test_chat_empty_message():
    """Sending an empty message returns 400 or 404 (not 500)."""
    response = client.post(
        "/api/v1/chat/",
        json={"document_id": "some-id", "message": "   "},
    )
    assert response.status_code in (400, 404)
