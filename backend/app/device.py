"""
Device detection for local AI inference.

Priority: CUDA (NVIDIA) > MPS (Apple Silicon) > CPU
"""
import logging
import os

logger = logging.getLogger(__name__)


def detect_device() -> str:
    """
    Detect the best available compute device.
    Returns 'cuda', 'mps', or 'cpu'.
    """
    # On Fly.io, we are always on CPU-only VMs. Avoid importing torch entirely.
    if os.getenv("FLY_APP_NAME"):
        logger.info("🟢 Running on Fly.io — defaulting to CPU")
        return "cpu"

    try:
        import torch

        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            vram = torch.cuda.get_device_properties(0).total_memory / 1e9
            logger.info(f"🟢 GPU detected: {gpu_name} ({vram:.1f}GB VRAM) — using CUDA")
            return "cuda"

        if torch.backends.mps.is_available():
            logger.info("🟢 Apple Silicon detected — using MPS")
            return "mps"

    except ImportError:
        pass

    logger.info("🟡 No GPU detected — using CPU")
    return "cpu"


def get_device_info() -> dict:
    """Return a dict with device details for the health endpoint."""
    if os.getenv("FLY_APP_NAME"):
        return {"device": "cpu", "gpu_name": None}

    try:
        import torch

        if torch.cuda.is_available():
            props = torch.cuda.get_device_properties(0)
            return {
                "device": "cuda",
                "gpu_name": props.name,
                "vram_gb": round(props.total_memory / 1e9, 1),
            }

        if torch.backends.mps.is_available():
            return {"device": "mps", "gpu_name": "Apple Silicon"}

    except ImportError:
        pass

    return {"device": "cpu", "gpu_name": None}


# Cached at import time — called once when the module is first imported
DEVICE = detect_device()
