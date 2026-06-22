from fastapi import APIRouter, HTTPException, status

from app.schemas import ChatRequest, ChatResponse
from app.services import chat_service
from app.services.document_service import get_document

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Send a message about a document and receive an AI-generated answer
    with source references.
    """
    # Validate document exists
    doc = get_document(request.document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{request.document_id}' not found. Please upload it first.",
        )

    if not request.message.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message cannot be empty.",
        )

    try:
        response = await chat_service.chat_with_document(
            doc_id=request.document_id,
            message=request.message,
            conversation_history=request.conversation_history or [],
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat error: {str(e)}. Make sure Ollama is running with the correct models.",
        )

    return response
