from langchain_ollama import ChatOllama
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferWindowMemory
from langchain.prompts import PromptTemplate

from app.config import settings
from app.schemas import ChatResponse, SourceChunk
from app.services.document_service import load_vector_store


# ── Prompt ────────────────────────────────────────────────────────────────────
QA_PROMPT = PromptTemplate(
    template="""You are DocChat, a helpful assistant that answers questions based on the provided document context.

Use ONLY the information from the context below to answer. If the answer is not in the context, say:
"I couldn't find this information in the document. Could you try rephrasing or ask something else?"

Be concise, accurate, and friendly. When relevant, mention which part of the document supports your answer.

Context:
{context}

Chat History:
{chat_history}

Question: {question}

Answer:""",
    input_variables=["context", "chat_history", "question"],
)


async def chat_with_document(
    doc_id: str,
    message: str,
    conversation_history: list[dict],
) -> ChatResponse:
    """
    Perform a RAG query: retrieve relevant chunks from FAISS,
    then generate an answer via Ollama.
    """
    # 1. Load vector store
    vector_store = load_vector_store(doc_id)
    if not vector_store:
        raise ValueError(f"Document '{doc_id}' not found or not indexed.")

    # 2. Build retriever
    retriever = vector_store.as_retriever(
        search_type="similarity",
        search_kwargs={"k": settings.retriever_k},
    )

    # 3. Build Ollama LLM
    llm = ChatOllama(
        base_url=settings.ollama_base_url,
        model=settings.ollama_chat_model,
        temperature=0.1,  # low temp for factual Q&A
    )

    # 4. Build memory from conversation history
    memory = ConversationBufferWindowMemory(
        memory_key="chat_history",
        return_messages=True,
        k=5,  # keep last 5 exchanges
        output_key="answer",
    )
    for entry in conversation_history[-10:]:  # cap history
        if entry.get("role") == "user":
            memory.chat_memory.add_user_message(entry["content"])
        elif entry.get("role") == "assistant":
            memory.chat_memory.add_ai_message(entry["content"])

    # 5. Build chain
    chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=retriever,
        memory=memory,
        combine_docs_chain_kwargs={"prompt": QA_PROMPT},
        return_source_documents=True,
        verbose=False,
    )

    # 6. Run
    result = chain.invoke({"question": message})

    # 7. Extract source chunks
    sources = []
    seen = set()
    for doc in result.get("source_documents", []):
        content = doc.page_content[:300].strip()
        page = doc.metadata.get("page", 0) + 1  # 0-indexed → 1-indexed
        key = (content[:50], page)
        if key not in seen:
            seen.add(key)
            sources.append(SourceChunk(content=content, page=page))

    return ChatResponse(
        answer=result["answer"],
        sources=sources,
        document_id=doc_id,
    )
