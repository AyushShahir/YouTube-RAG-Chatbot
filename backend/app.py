import os
import re
import shutil
from pathlib import Path
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from dotenv import load_dotenv

from youtube_transcript_api import YouTubeTranscriptApi
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
CHROMA_DIR = DATA_DIR / "chroma_db"

DATA_DIR.mkdir(exist_ok=True)

app = Flask(
    __name__,
    template_folder="../templates",
    static_folder="../static",
    static_url_path=""
)

CORS(app)

# Active RAG session state
state = {
    "video_id": None,
    "chain": None
}


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


def fetch_transcript(video_id: str):
    api = YouTubeTranscriptApi()
    transcript = api.fetch(video_id)

    transcript_data = []
    for snippet in transcript:
        transcript_data.append(
            {
                "text": snippet.text,
                "start": snippet.start,
                "duration": snippet.duration,
            }
        )

    return transcript_data


def create_chunks(transcript_data):
    full_transcript = " ".join(item["text"] for item in transcript_data)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=600,
        chunk_overlap=100,
    )

    text_chunks = splitter.split_text(full_transcript)

    documents = []
    for i, chunk in enumerate(text_chunks):
        documents.append(
            Document(
                page_content=chunk,
                metadata={"chunk_id": i}
            )
        )

    return documents


def create_vector_store(documents):
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    if CHROMA_DIR.exists():
        try:
            shutil.rmtree(CHROMA_DIR)
        except Exception:
            pass

    CHROMA_DIR.mkdir(exist_ok=True)

    vector_store = Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        persist_directory=str(CHROMA_DIR),
    )

    return vector_store


def create_rag_chain(retriever):
    system_prompt = """
You are an expert YouTube Transcript Question Answering Assistant.

You answer questions using ONLY the transcript context provided.

Follow these rules carefully:

• Use only the transcript.
• Never invent facts or use external knowledge.
• When answering factual questions, quote or summarize the relevant transcript.
• When answering high-level questions (such as "What is this video about?", "Summarize the video", "What is the main topic?", "List the key points"), synthesize information from all relevant transcript passages.
• The transcript may not literally contain phrases like "main topic" or "summary". Infer these from the overall discussion.
• If there are multiple themes, identify the primary one and briefly mention secondary topics.
• If the transcript is insufficient to answer confidently, reply exactly:

"I couldn't find that information in the video transcript."

Keep answers clear, concise, and faithful to the transcript.

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

    def format_docs(docs):
        return "\n\n---\n\n".join(doc.page_content for doc in docs)

    chain = (
        {
            "context": retriever | format_docs,
            "question": RunnablePassthrough(),
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

        state["chain"] = create_rag_chain(retriever)
        state["video_id"] = video_id

        return jsonify({
            "message": "Video processed and indexed successfully!",
            "video_id": video_id
        })

    except Exception as e:
        return jsonify({"error": f"Failed to process video: {str(e)}"}), 500


@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json() or {}
    question = data.get("question")

    if not question:
        return jsonify({"error": "Question is required."}), 400

    if not state.get("chain"):
        return jsonify({
            "error": "No video has been processed yet. Please process a video first."
        }), 400

    try:
        answer = state["chain"].invoke(question)
        return jsonify({"answer": answer})
    except Exception as e:
        return jsonify({"error": f"Failed to generate answer: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )
