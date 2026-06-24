from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

from app.config import settings
from app.schemas import ChatResponse, SourceChunk
from app.services.document_service import load_vector_store
# Note: embeddings are handled by document_service via HuggingFaceEmbeddings singleton


def _get_llm():
    """
    Returns the appropriate LLM instance.
    Prioritizes Groq API Key -> OpenAI API Key -> Fallback to Local Ollama.
    """
    if settings.groq_api_key:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=settings.groq_api_key,
            model="llama-3.2-3b-preview",
            temperature=0.1,
        )
    elif settings.openai_api_key:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            api_key=settings.openai_api_key,
            model="gpt-4o-mini",
            temperature=0.1,
        )
    else:
        from langchain_ollama import ChatOllama
        return ChatOllama(
            base_url=settings.ollama_base_url,
            model=settings.ollama_chat_model,
            temperature=0.1,
        )



# ── Prompts ───────────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are DocChat, a helpful assistant that answers questions \
based exclusively on the provided document context.

Use ONLY the information from the context below. If the answer is not in the \
context, say: "I couldn't find this information in the document."

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


def _build_history(conversation_history: list[dict]) -> list:
    messages = []
    for entry in conversation_history[-10:]:  # cap at last 10 turns
        role = entry.get("role", "")
        content = entry.get("content", "")
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "assistant":
            messages.append(AIMessage(content=content))
    return messages


async def chat_with_document(
    doc_id: str,
    message: str,
    conversation_history: list[dict],
) -> ChatResponse:
    """
    RAG pipeline using LangChain LCEL:
    1. Retrieve top-K chunks from FAISS via similarity search
    2. Build prompt with context + history
    3. Call Ollama LLM
    4. Return answer + source citations
    """
    # 1. Load vector store
    vector_store = load_vector_store(doc_id)
    if not vector_store:
        raise ValueError(f"Document '{doc_id}' not found or not indexed.")

    # 2. Retrieve relevant chunks
    retriever = vector_store.as_retriever(
        search_type="similarity",
        search_kwargs={"k": settings.retriever_k},
    )
    source_docs = retriever.invoke(message)

    # 3. Get LLM (Ollama or Cloud Fallback)
    llm = _get_llm()


    # 4. Build LCEL chain
    chain = (
        {
            "context":  lambda _: _format_docs(source_docs),
            "question": RunnablePassthrough(),
            "history":  lambda _: _build_history(conversation_history),
        }
        | prompt
        | llm
        | StrOutputParser()
    )

    # 5. Invoke
    answer = chain.invoke(message)

    # 6. Build source citations (deduplicated)
    sources = []
    seen = set()
    for doc in source_docs:
        content = doc.page_content[:300].strip()
        page = doc.metadata.get("page", 0) + 1  # 0-indexed → 1-indexed
        key = (content[:50], page)
        if key not in seen:
            seen.add(key)
            sources.append(SourceChunk(content=content, page=page))

    return ChatResponse(
        answer=answer,
        sources=sources,
        document_id=doc_id,
    )
