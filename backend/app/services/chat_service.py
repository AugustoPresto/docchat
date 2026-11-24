import asyncio
from collections.abc import AsyncIterator

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from app.config import get_provider, settings
from app.schemas import ChatResponse, HistoryMessage, SourceChunk
from app.services.document_service import load_vector_store


def _get_llm():
    """Return the chat model. Priority: Groq → OpenAI → local Ollama."""
    provider, model = get_provider()
    if provider == "groq":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=settings.groq_api_key,
            model=model,
            temperature=0.1,
        )
    if provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(api_key=settings.openai_api_key, model=model, temperature=0.1)

    from langchain_ollama import ChatOllama
    return ChatOllama(base_url=settings.ollama_base_url, model=model, temperature=0.1)


# ── Prompts ───────────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are DocChat, a helpful assistant that answers questions \
based exclusively on the provided document context.

Use ONLY the information from the context below. If the answer is not in the \
context, say: "I couldn't find this information in the document."
Answer in the same language as the user's question.

Be concise, accurate, and friendly.

Context:
{context}"""

prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    MessagesPlaceholder(variable_name="history"),
    ("human", "{question}"),
])


def _format_docs(docs) -> str:
    return "\n\n---\n\n".join(d.page_content for d in docs)


def _build_history(conversation_history: list[HistoryMessage]) -> list:
    messages = []
    for entry in conversation_history[-10:]:  # cap at last 10 turns
        cls = HumanMessage if entry.role == "user" else AIMessage
        messages.append(cls(content=entry.content))
    return messages


def _sources(source_docs) -> list[SourceChunk]:
    sources, seen = [], set()
    for doc in source_docs:
        content = doc.page_content[:300].strip()
        page = doc.metadata.get("page", 0) + 1  # 0-indexed → 1-indexed
        key = (content[:50], page)
        if key not in seen:
            seen.add(key)
            sources.append(SourceChunk(content=content, page=page))
    return sources


async def _prepare(doc_id: str, message: str, history: list[HistoryMessage]):
    """Retrieve context and build the prompt inputs (off the event loop)."""
    vector_store = await asyncio.to_thread(load_vector_store, doc_id)
    if not vector_store:
        raise LookupError(f"Document '{doc_id}' not found or not indexed.")

    source_docs = await vector_store.asimilarity_search(message, k=settings.retriever_k)
    inputs = {
        "context": _format_docs(source_docs),
        "question": message,
        "history": _build_history(history),
    }
    return source_docs, inputs


async def chat_with_document(
    doc_id: str,
    message: str,
    conversation_history: list[HistoryMessage],
) -> ChatResponse:
    """RAG: retrieve top-K chunks → prompt with history → LLM → answer + citations."""
    source_docs, inputs = await _prepare(doc_id, message, conversation_history)
    chain = prompt | _get_llm() | StrOutputParser()
    answer = await chain.ainvoke(inputs)
    return ChatResponse(answer=answer, sources=_sources(source_docs), document_id=doc_id)


async def stream_chat(
    doc_id: str,
    message: str,
    conversation_history: list[HistoryMessage],
) -> AsyncIterator[dict]:
    """
    Same pipeline as chat_with_document but yields events as they happen:
    {"type": "sources", ...} first, then {"type": "token", ...} per chunk.
    """
    source_docs, inputs = await _prepare(doc_id, message, conversation_history)
    yield {"type": "sources", "sources": [s.model_dump() for s in _sources(source_docs)]}

    chain = prompt | _get_llm() | StrOutputParser()
    async for token in chain.astream(inputs):
        if token:
            yield {"type": "token", "content": token}
