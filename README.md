# YouTube RAG Chatbot

Ask questions about any YouTube video and get answers grounded in its transcript — with automatic fallback to live web search for questions about the video's subject that aren't covered in the transcript itself.

## Features

- 🎥 Paste any YouTube URL to fetch its transcript and metadata automatically
- 💬 Ask questions in a chat interface; answers are retrieved from the transcript using RAG (Retrieval-Augmented Generation)
- 🧠 **Smart routing**: questions are automatically classified into one of three categories:
  - **In video** — answered directly from the transcript
  - **Related, but not in the video** — answered using live web search (Tavily), since it's still about the video's subject
  - **Unrelated** — politely declined
- 📊 Video metadata display (title, channel, views, duration, published date)
- ✨ Clean, Gemini-inspired chat UI built with Streamlit

## Tech Stack

- **Frontend:** Streamlit
- **LLM:** Google Gemini (`gemini-2.5-flash`) via LangChain
- **Embeddings:** HuggingFace `sentence-transformers/all-MiniLM-L6-v2` (local, no API cost)
- **Vector Store:** ChromaDB
- **Web Search:** Tavily Search API
- **Transcript Fetching:** `youtube-transcript-api`

## Setup

1. Clone the repo and install dependencies:
```bash
   uv sync
```
   (or `pip install -e .`)

2. Create a `.env` file in the project root with:

## How It Works

1. User submits a YouTube URL → transcript + metadata are fetched
2. Transcript is chunked and embedded into ChromaDB
3. On each question, the router:
   - Retrieves the most relevant transcript chunks
   - Classifies the question as in-video / related-external / unrelated
   - Routes to the RAG chain, a web-search-augmented chain, or a refusal accordingly
4. Answer is displayed in the chat, labeled with its source