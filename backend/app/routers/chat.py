import json
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from app.config import get_provider
from app.deps import get_owner
from app.schemas import ChatRequest, ChatResponse
from app.services import chat_service
from app.services.document_service import get_document

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


def _llm_error_message() -> str:
    provider, model = get_provider()
    if provider == "ollama":
        return (
            f"Could not get an answer from the local model. Make sure Ollama is running "
            f"and the model is installed (ollama pull {model})."
        )
    return f"The AI provider ({provider}) returned an error. Please try again in a moment."


def _validate(request: ChatRequest, owner: str | None) -> None:
    doc = get_document(request.document_id, owner)
    if not doc:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            f"Document '{request.document_id}' not found. Please upload it first.",
        )
    if doc.status != "ready":
        raise HTTPException(status.HTTP_409_CONFLICT, "This document is not ready yet.")
    if not request.message.strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Message cannot be empty.")


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest, owner: str | None = Depends(get_owner)):
    """Ask a question about a document; returns the full answer with sources."""
    _validate(request, owner)
    try:
        return await chat_service.chat_with_document(
            doc_id=request.document_id,
            message=request.message,
            conversation_history=request.conversation_history,
        )
    except LookupError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))
    except ValueError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e))
    except Exception:
        logger.exception("Chat failed for document %s", request.document_id)
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, _llm_error_message())


@router.post("/stream")
async def chat_stream(request: ChatRequest, owner: str | None = Depends(get_owner)):
    """
    Streaming version of /chat/. Returns newline-delimited JSON events:
    {"type":"sources",...}, {"type":"token","content":...}*, then
    {"type":"done"} or {"type":"error","detail":...}.
    """
    _validate(request, owner)

    async def events():
        try:
            async for event in chat_service.stream_chat(
                doc_id=request.document_id,
                message=request.message,
                conversation_history=request.conversation_history,
            ):
                yield json.dumps(event) + "\n"
            yield json.dumps({"type": "done"}) + "\n"
        except (LookupError, ValueError) as e:
            yield json.dumps({"type": "error", "detail": str(e)}) + "\n"
        except Exception:
            logger.exception("Streaming chat failed for document %s", request.document_id)
            yield json.dumps({"type": "error", "detail": _llm_error_message()}) + "\n"

    return StreamingResponse(
        events(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
