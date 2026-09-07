import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from dotenv import load_dotenv

from youtube_transcript_api import YouTubeTranscriptApi
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

app = Flask(
    __name__,
    template_folder="../templates",
    static_folder="../static",
    static_url_path=""
)

CORS(app)


class AppState:
    video_id: Optional[str] = None
    chain: Optional[Any] = None
    retriever: Optional[Any] = None
    conversation_history: List[Dict[str, str]] = []


state = AppState()


def add_to_memory(question: str, answer: str) -> None:
    """Store the current question and answer in conversation memory."""

    state.conversation_history.append({
        "role": "user",
        "content": question
    })

    state.conversation_history.append({
        "role": "assistant",
        "content": answer
    })


def format_memory() -> str:
    """Convert conversation history into text for Gemini."""

    if not state.conversation_history:
        return "No previous conversation."

    history = []

    for message in state.conversation_history:
        role = "User" if message["role"] == "user" else "Assistant"
        history.append(f"{role}: {message['content']}")

    return "\n".join(history)


def clear_memory() -> None:
    """Clear conversation memory when a new video is processed."""

    state.conversation_history = []


def format_timestamp(seconds: float | int) -> str:
    """Convert seconds into MM:SS or HH:MM:SS format."""

    total_seconds = int(seconds)

    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60

    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    return f"{minutes:02d}:{secs:02d}"


def create_timestamp_url(video_id: str, seconds: float | int) -> str:
    """Create a YouTube URL that starts at a specific timestamp."""

    return f"https://www.youtube.com/watch?v={video_id}&t={int(seconds)}s"


def extract_video_id(url: str) -> str | None:
    pattern = (
        r"(?:https?://)?(?:www\.)?"
        r"(?:youtube\.com/(?:watch\?v=|embed/|shorts/|live/)|youtu\.be/)"
        r"([a-zA-Z0-9_-]{11})"
    )

    match = re.search(pattern, url)

    if not match:
        return None

    return match.group(1)


def fetch_transcript(video_id: str) -> List[Dict[str, Any]]:
    api = YouTubeTranscriptApi()
    transcript = None

    # 1. Try direct fetch with v1 api.fetch or legacy classmethod get_transcript
    try:
        if hasattr(api, "fetch"):
            transcript = api.fetch(video_id)
        elif hasattr(YouTubeTranscriptApi, "get_transcript"):
            transcript = YouTubeTranscriptApi.get_transcript(video_id)
    except Exception:
        pass

    # 2. If direct fetch failed, try list / list_transcripts fallback
    if transcript is None:
        try:
            if hasattr(api, "list"):
                transcript_list = api.list(video_id)
            elif hasattr(api, "list_transcripts"):
                transcript_list = api.list_transcripts(video_id)
            elif hasattr(YouTubeTranscriptApi, "list_transcripts"):
                transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            else:
                raise RuntimeError("No transcript list method found on YouTubeTranscriptApi.")

            try:
                transcript_obj = transcript_list.find_transcript(['en', 'en-US', 'en-GB'])
            except Exception:
                try:
                    transcript_obj = transcript_list.find_generated_transcript(['en'])
                except Exception:
                    # Translate the first available transcript to English
                    first_t = next(iter(transcript_list))
                    transcript_obj = first_t.translate('en')

            if hasattr(transcript_obj, "fetch"):
                transcript = transcript_obj.fetch()
            else:
                transcript = transcript_obj
        except Exception as inner_e:
            raise RuntimeError(
                f"Could not retrieve transcript for video '{video_id}'. Captions/transcripts might be disabled, unavailable, or in an unsupported language."
            ) from inner_e

    transcript_data = []
    for snippet in transcript:
        text = getattr(snippet, "text", None) if not isinstance(snippet, dict) else snippet.get("text")
        start = getattr(snippet, "start", None) if not isinstance(snippet, dict) else snippet.get("start")
        duration = getattr(snippet, "duration", None) if not isinstance(snippet, dict) else snippet.get("duration")

        if text is not None and start is not None:
            transcript_data.append(
                {
                    "text": text,
                    "start": start,
                    "duration": duration or 0,
                }
            )

    if not transcript_data:
        raise RuntimeError(f"Transcript for video '{video_id}' is empty.")

    return transcript_data


def create_chunks(transcript_data: List[Dict[str, Any]], chunk_size: int = 600) -> List[Document]:
    """
    Create transcript chunks while preserving exact timestamp information.
    Combines transcript items without slicing words mid-character.
    """

    documents: List[Document] = []
    current_items: List[Dict[str, Any]] = []
    current_length = 0

    for item in transcript_data:
        current_items.append(item)
        current_length += len(item["text"])

        if current_length >= chunk_size:
            chunk_text = " ".join(i["text"] for i in current_items)
            documents.append(
                Document(
                    page_content=chunk_text.strip(),
                    metadata={
                        "chunk_id": len(documents),
                        "start": current_items[0]["start"],
                        "end": current_items[-1]["start"] + current_items[-1]["duration"]
                    }
                )
            )
            # Keep last item for context overlap while retaining accurate start timestamp
            current_items = current_items[-1:]
            current_length = len(current_items[0]["text"])

    if current_items:
        chunk_text = " ".join(i["text"] for i in current_items)
        documents.append(
            Document(
                page_content=chunk_text.strip(),
                metadata={
                    "chunk_id": len(documents),
                    "start": current_items[0]["start"],
                    "end": current_items[-1]["start"] + current_items[-1]["duration"]
                }
            )
        )

    return documents


def create_vector_store(documents: List[Document]) -> Chroma:
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    # Use in-memory Chroma to prevent file locking issues on Windows
    vector_store = Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
    )

    return vector_store


def create_rag_chain(retriever: Any) -> Any:
    system_prompt = """
You are an expert YouTube Transcript Question Answering Assistant.

You answer questions using ONLY the transcript context provided.

CRUCIAL INSTRUCTION FOR TIMESTAMPS:
Whenever you state a fact, answer a point, or present a topic summary, cite the corresponding timestamp from the transcript inline right after the relevant sentence, formatted strictly as (MM:SS) or (HH:MM:SS) (or (MM:SS - MM:SS) for time ranges).
Examples:
- "Scientific Breakthroughs: Hassabis emphasizes fundamental scientific challenges such as fusion energy (2:38)."
- "Evolution of AI: The discussion then moves toward agentic and multimodal AI systems (14:52)."

Do NOT invent timestamps; use the exact [Timestamp: MM:SS] markers provided in the transcript context below.

Use the conversation history only to understand references
and follow-up questions such as:
- "What about that?"
- "Why is it important?"
- "Who said that?"
- "Can you explain that further?"

Do NOT use information from the conversation history as factual
evidence. Factual answers must still come from the transcript.

If the transcript does not contain enough information, reply exactly:

"I couldn't find that information in the video transcript."

Conversation history:
{history}

Transcript:
{context}
"""

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("human", "{question}"),
        ]
    )

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0,
    )

    def format_docs(docs: List[Document]) -> str:
        formatted_chunks = []
        for doc in docs:
            start_sec = doc.metadata.get("start", 0)
            timestamp_str = format_timestamp(start_sec)
            formatted_chunks.append(f"[Timestamp: {timestamp_str}]\n{doc.page_content}")
        return "\n\n---\n\n".join(formatted_chunks)

    chain = (
        {
            "context": lambda x: format_docs(
                retriever.invoke(x["question"])
            ),
            "question": lambda x: x["question"],
            "history": lambda x: x["history"],
        }
        | prompt
        | llm
        | StrOutputParser()
    )

    return chain


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/process-video", methods=["POST"])
def process_video():
    data = request.get_json() or {}
    url = data.get("url")

    if not url:
        return jsonify({"error": "YouTube URL is required."}), 400

    video_id = extract_video_id(url)

    if not video_id:
        return jsonify({"error": "Invalid YouTube URL."}), 400

    try:
        transcript_data = fetch_transcript(video_id)
        documents = create_chunks(transcript_data)
        vector_store = create_vector_store(documents)

        retriever = vector_store.as_retriever(
            search_type="mmr",
            search_kwargs={
                "k": 8,
                "fetch_k": 20
            }
        )

        state.retriever = retriever
        state.chain = create_rag_chain(retriever)
        state.video_id = video_id

        # Start a fresh conversation for the new video
        clear_memory()

        return jsonify({
            "message": "Video processed and indexed successfully!",
            "video_id": video_id,
            "chunks": len(documents)
        })

    except Exception as e:
        return jsonify({"error": f"Failed to process video: {str(e)}"}), 500


@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json() or {}
    question = data.get("question")

    if not question:
        return jsonify({"error": "Question is required."}), 400

    if not state.chain or not state.retriever or not state.video_id:
        return jsonify({
            "error": "No video has been processed yet. Please process a video first."
        }), 400

    try:
        history = format_memory()

        docs = state.retriever.invoke(question)

        answer = state.chain.invoke({
            "question": question,
            "history": history
        })

        add_to_memory(question, answer)

        sources = []
        if "couldn't find that information" not in str(answer).lower():
            seen_seconds = set()
            for doc in docs:
                start = doc.metadata.get("start")
                if start is None:
                    continue

                sec = int(start)
                if sec not in seen_seconds:
                    seen_seconds.add(sec)
                    sources.append({
                        "timestamp": format_timestamp(sec),
                        "seconds": sec,
                        "url": create_timestamp_url(
                            state.video_id,
                            sec
                        )
                    })

        return jsonify({
            "answer": answer,
            "sources": sources
        })

    except Exception as e:
        return jsonify({
            "error": f"Failed to generate answer: {str(e)}"
        }), 500


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )
