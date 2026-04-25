# 10-K Whisperer 📊

An intelligent Retrieval-Augmented Generation (RAG) application for analyzing SEC filings and financial documents using Streamlit and OpenAI's GPT-4.

## Features

✨ **Document Upload & Processing**
- Upload PDF documents (10-K filings, annual reports, etc.)
- Automatic text extraction and chunking
- Fast vector store creation with FAISS

📋 **Executive Summary**
- AI-generated 3-bullet summary of uploaded documents
- Quick insight into key findings

💬 **Contextual Q&A**
- Chat interface for asking questions about documents
- AI answers based only on document content
- Source document references for transparency

🚀 **Performance Optimized**
- Cached embedding model for fast processing
- Session state management to avoid re-embedding
- Lightweight, single-file architecture

## Architecture

- **Framework**: Streamlit (UI, chat, file handling)
- **RAG Orchestration**: LangChain
- **PDF Processing**: PyPDF2
- **Embeddings**: HuggingFace (all-MiniLM-L6-v2)
- **Vector Store**: FAISS (local, in-memory)
- **LLM**: OpenAI GPT-4 via LangChain
- **Session Management**: Streamlit session_state

## Prerequisites

- Python 3.8 or higher
- OpenAI API key (paid tier required for GPT-4)

## Setup Instructions

### 1. Clone or Download the Project

```bash
cd c:\Users\monis\Desktop\AIFB
```

### 2. Create a Python Virtual Environment (Recommended)

```bash
python -m venv venv
```

Activate the environment:

**Windows (PowerShell):**
```powershell
.\venv\Scripts\Activate.ps1
```

**Windows (Command Prompt):**
```bash
venv\Scripts\activate.bat
```

**macOS/Linux:**
```bash
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Set Up the OpenAI API Key

#### Get Your API Key:
1. Navigate to https://platform.openai.com/api-keys
2. Sign in with your OpenAI account (or create one)
3. Click "+ Create new secret key"
4. Copy your API key

#### Create a `.env` File:

Create a `.env` file in the project directory with:

```
OPENAI_API_KEY=your_actual_openai_api_key_here
```

**Important**: Never commit this file to version control. Add `.env` to your `.gitignore`.

Alternatively, you can copy `.env.example` and update it:

```bash
copy .env.example .env
# Then edit .env with your actual API key
```

### 5. Run the Application

```bash
streamlit run app.py
```

The app will open in your default browser at `http://localhost:8501`

## Usage

1. **Upload a Document**
   - Click "Upload a PDF" in the sidebar
   - Select a 10-K filing or financial document
   - Click "Process Document"

2. **Wait for Processing**
   - The app will extract text, create embeddings, and build a vector store
   - An executive summary will be generated

3. **Ask Questions**
   - Type your question in the chat input at the bottom
   - The AI will answer based on the document content
   - Chat history is preserved in the session

4. **View Sources**
   - Expand "Sources" to see which document sections were used

## Project Structure

```
AIFB/
├── app.py                 # Main Streamlit application
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables (create this)
├── .env.example          # Template for .env file
└── README.md             # This file
```

## Technical Details

### Session State Management

The app uses `st.session_state` to persist:
- `vector_store`: The FAISS vector store (prevents re-embedding on every query)
- `chat_history`: Conversation history
- `document_name`: Name of the uploaded document
- `document_text`: Full text of the document

### Caching Strategy

- `@st.cache_resource` for embedding model (loaded once per session)
- `@st.cache_resource` for LLM (loaded once per session)

### Document Processing Pipeline

1. **Extraction**: PyPDF2 extracts text from PDF
2. **Chunking**: RecursiveCharacterTextSplitter creates 1000-token chunks with 200-token overlap
3. **Embedding**: HuggingFace embeddings convert chunks to vectors
4. **Vector Store**: FAISS stores embeddings for fast retrieval
5. **Retrieval**: Top 4 relevant chunks retrieved for each query
6. **Generation**: OpenAI GPT-4 generates answers with retrieved context

## Troubleshooting

### "OPENAI_API_KEY environment variable not set"
- Ensure you've created a `.env` file
- Verify the environment variable name is exactly `OPENAI_API_KEY`
- Restart the Streamlit app after creating the `.env` file

### PDF Processing Errors
- Ensure the PDF is not corrupted
- Try a smaller PDF first to test
- Check that PDF text is extractable (not image-scanned)

### Slow Performance
- First time loading the embedding model takes longer (it's cached after)
- Keep documents to reasonable sizes (under 50 pages recommended)
- FAISS operations are fast; network (API calls) may be the bottleneck

### Out of Memory Errors
- Reduce `chunk_size` in `chunk_documents()` function
- Process smaller documents
- Clear browser cache and restart the app

## Security Considerations

- ✅ Your API key is loaded from `.env` and never committed to git
- ✅ Documents are processed locally (not sent to storage)
- ✅ Only query text and retrieved context are sent to OpenAI
- ⚠️ Keep your `.env` file private and never share it
- ⚠️ Be aware of API usage costs (OpenAI charges per token used)

## Performance Tips

- First document load initializes the embedding model (takes ~10 seconds)
- Subsequent documents/queries use cached model
- Limit documents to 30-50 pages for best performance
- Use specific questions for better answers

## API Cost Estimation

OpenAI GPT-4 API:
- Pricing: Based on input/output tokens (~0.03-0.06 per 1K tokens)
- No free tier, but generous credits for new accounts
- Monitor usage at https://platform.openai.com/account/usage/overview

Check https://openai.com/pricing for current rates.

## Future Enhancements

- Support for multiple documents in one session
- Batch upload and processing
- Export chat history to markdown/PDF
- Fine-tuned prompts for different document types
- Support for other LLM providers (Anthropic Claude, Cohere, etc.)
- Document comparison features

## License

This project is open source. Use it freely for personal and commercial projects.

## Support

For issues or questions:
1. Check the Troubleshooting section above
2. Review Streamlit documentation: https://docs.streamlit.io
3. Check LangChain documentation: https://python.langchain.com
4. OpenAI API docs: https://platform.openai.com/docs

---

**Happy analyzing! 📊**

Built with Streamlit + LangChain + OpenAI GPT-4
