import os

import faiss
import numpy as np
import streamlit as st
from dotenv import load_dotenv
from PyPDF2 import PdfReader

# Load environment variables
load_dotenv()

# Configure page
st.set_page_config(
    page_title="10-K Whisperer",
    page_icon=":bar_chart:",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("10-K Whisperer")
st.markdown("*Intelligent analysis of SEC filings and financial documents*")


# ============================================================================
# CACHED FUNCTIONS
# ============================================================================

@st.cache_resource
def load_embedding_model():
    """Load and cache the embedding model."""
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")


@st.cache_resource
def load_llm():
    """Load and cache the LLM."""
    from langchain_google_genai import ChatGoogleGenerativeAI

    api_key = os.getenv("GOOGLE_AI_API_KEY")
    if not api_key:
        raise ValueError(
            "GOOGLE_AI_API_KEY environment variable not set. "
            "Please set it in your .env file."
        )

    return ChatGoogleGenerativeAI(
        model=os.getenv("GOOGLE_MODEL", "gemini-2.5-flash"),
        google_api_key=api_key,
        temperature=0.3,
    )


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def extract_text_from_pdf(pdf_file):
    """Extract text from an uploaded PDF file."""
    try:
        pdf_reader = PdfReader(pdf_file)
        text_parts = []
        for page in pdf_reader.pages:
            text_parts.append(page.extract_text() or "")
        return "\n".join(text_parts).strip()
    except Exception as exc:
        st.error(f"Error reading PDF: {exc}")
        return None


def _split_large_block(block, chunk_size, chunk_overlap):
    """Split an oversized block into overlapping chunks."""
    chunks = []
    start = 0

    while start < len(block):
        end = min(start + chunk_size, len(block))
        chunk = block[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(block):
            break
        start = max(end - chunk_overlap, start + 1)

    return chunks


def chunk_documents(text, chunk_size=1400, chunk_overlap=120):
    """Split text into chunks while trying to preserve paragraph boundaries."""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    paragraphs = [paragraph.strip() for paragraph in normalized.split("\n\n") if paragraph.strip()]

    chunks = []
    current = ""

    for paragraph in paragraphs:
        candidate = f"{current}\n\n{paragraph}".strip() if current else paragraph
        if len(candidate) <= chunk_size:
            current = candidate
            continue

        if current:
            chunks.append(current)
            current = ""

        if len(paragraph) <= chunk_size:
            current = paragraph
        else:
            chunks.extend(_split_large_block(paragraph, chunk_size, chunk_overlap))

    if current:
        chunks.append(current)

    if not chunks and normalized.strip():
        chunks = _split_large_block(normalized.strip(), chunk_size, chunk_overlap)

    return chunks


def create_vector_store(chunks, embedding_model):
    """Create an in-memory FAISS index from document chunks."""
    try:
        if not chunks:
            raise ValueError("No text chunks were generated from the document.")

        embeddings = embedding_model.encode(
            chunks,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        embeddings = np.asarray(embeddings, dtype="float32")

        index = faiss.IndexFlatIP(embeddings.shape[1])
        index.add(embeddings)

        return {
            "index": index,
            "chunks": chunks,
            "dimension": embeddings.shape[1],
        }
    except Exception as exc:
        st.error(f"Error creating vector store: {exc}")
        return None


def retrieve_relevant_chunks(query, vector_store, embedding_model, k=4):
    """Retrieve the most relevant chunks for a user query."""
    query_embedding = embedding_model.encode(
        [query],
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    query_embedding = np.asarray(query_embedding, dtype="float32")

    top_k = min(k, len(vector_store["chunks"]))
    scores, indices = vector_store["index"].search(query_embedding, top_k)

    results = []
    for score, index in zip(scores[0], indices[0]):
        if index == -1:
            continue
        results.append(
            {
                "content": vector_store["chunks"][index],
                "score": float(score),
            }
        )

    return results


def generate_summary(text, llm):
    """Generate a 3-bullet executive summary using the LLM."""
    summary_prompt = """You are a financial analyst.
Create exactly 3 short bullet points summarizing the document excerpt below.
Each bullet must be a single sentence and start with "- ".

Document excerpt:
{text}

Executive summary:"""

    try:
        truncated_text = text[:3000]
        response = llm.invoke(summary_prompt.format(text=truncated_text))
        return response.content
    except Exception as exc:
        st.error(f"Error generating summary: {exc}")
        return None


def answer_question(question, vector_store, embedding_model, llm):
    """Answer a question using retrieved document context."""
    sources = retrieve_relevant_chunks(question, vector_store, embedding_model)
    if not sources:
        return "I don't have enough information to answer this question.", []

    context = "\n\n---\n\n".join(source["content"] for source in sources)

    prompt = """Use only the context below to answer the user's question.
If the answer is not supported by the context, say "I don't have enough information to answer this question."
Be concise and specific.

Context:
{context}

Question: {question}

Answer:"""

    response = llm.invoke(prompt.format(context=context, question=question))
    return response.content, sources


# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================

if "initialized" not in st.session_state:
    st.session_state.initialized = True
    st.session_state.vector_store = None
    st.session_state.chat_history = []
    st.session_state.document_name = None
    st.session_state.document_text = None
    st.session_state.summary = None
    st.session_state.chunk_count = 0


# ============================================================================
# SIDEBAR: FILE UPLOAD
# ============================================================================

with st.sidebar:
    st.header("Document Upload")
    uploaded_file = st.file_uploader(
        "Upload a PDF (10-K, annual report, etc.)",
        type=["pdf"],
        help="Upload a financial document for analysis",
    )

    if uploaded_file and st.button("Process Document", key="process_btn"):
        with st.spinner("Processing document..."):
            text = extract_text_from_pdf(uploaded_file)

            if text:
                st.session_state.document_text = text
                st.session_state.document_name = uploaded_file.name
                st.session_state.summary = None
                st.session_state.vector_store = None
                st.session_state.chat_history = []

                chunks = chunk_documents(text)
                st.session_state.chunk_count = len(chunks)
                st.success(f"Document processed ({len(chunks)} chunks)")

                with st.spinner("Creating vector store..."):
                    embedding_model = load_embedding_model()
                    vector_store = create_vector_store(chunks, embedding_model)
                    st.session_state.vector_store = vector_store
                    if vector_store:
                        st.success("Vector store created")

    st.divider()

    if st.session_state.document_name:
        st.subheader("Current Document")
        st.info(
            f"**{st.session_state.document_name}**\n\n"
            f"Status: Ready for Q&A\n\n"
            f"Chunks: {st.session_state.chunk_count}"
        )


# ============================================================================
# MAIN CONTENT AREA
# ============================================================================

if st.session_state.vector_store and st.session_state.document_name:
    st.subheader("Executive Summary")
    if st.session_state.summary:
        with st.container():
            st.markdown(st.session_state.summary)
    elif st.button("Generate Summary", key="generate_summary_btn"):
        with st.spinner("Generating summary..."):
            try:
                llm = load_llm()
                summary = generate_summary(st.session_state.document_text, llm)
                if summary:
                    st.session_state.summary = summary
                    st.rerun()
            except Exception as exc:
                st.error(f"Error generating summary: {exc}")
    else:
        st.caption("Summary is generated on demand to keep document processing fast.")

    st.divider()

    st.subheader("Ask Questions About the Document")

    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    user_input = st.chat_input(
        "Ask a question about the document...",
        key="chat_input",
    )

    if user_input:
        st.session_state.chat_history.append(
            {
                "role": "user",
                "content": user_input,
            }
        )

        with st.chat_message("user"):
            st.markdown(user_input)

        with st.spinner("Thinking..."):
            try:
                llm = load_llm()
                embedding_model = load_embedding_model()
                response, sources = answer_question(
                    user_input,
                    st.session_state.vector_store,
                    embedding_model,
                    llm,
                )

                st.session_state.chat_history.append(
                    {
                        "role": "assistant",
                        "content": response,
                    }
                )

                with st.chat_message("assistant"):
                    st.markdown(response)

                if sources:
                    with st.expander("Sources"):
                        for i, source in enumerate(sources, 1):
                            excerpt = source["content"][:200].replace("\n", " ")
                            st.caption(f"Source {i} (score {source['score']:.3f}): {excerpt}...")

            except Exception as exc:
                st.error(f"Error generating response: {exc}")

else:
    st.info(
        "**Welcome to 10-K Whisperer!**\n\n"
        "1. Upload a PDF document using the sidebar\n"
        "2. Click 'Process Document' to analyze it\n"
        "3. Ask questions about the document in the chat interface\n\n"
        "Supported documents: 10-K filings, annual reports, SEC documents, and more."
    )

    with st.expander("How it works"):
        st.markdown(
            """
            - **Document Processing**: Your PDF is converted to text and split into chunks
            - **Embeddings**: Each chunk is converted into a dense embedding locally
            - **Vector Store**: Embeddings are stored in a local FAISS index
            - **Retrieval**: Relevant chunks are fetched when you ask a question
            - **Generation**: Google Gemini generates answers from the retrieved context

            Most document processing happens locally on your machine. The retrieved text is sent to Google only when you request a summary or ask a question.
            """
        )
