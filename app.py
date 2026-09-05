import os
import re
import shutil
from pathlib import Path

import streamlit as st
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


# ============================================================
# 1. CONFIGURATION
# ============================================================

load_dotenv()

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
CHROMA_DIR = DATA_DIR / "chroma_db"

DATA_DIR.mkdir(exist_ok=True)
CHROMA_DIR.mkdir(exist_ok=True)


# ============================================================
# 2. PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="YouTube RAG Chatbot",
    page_icon="🎥",
    layout="wide",
)


# ============================================================
# 3. HELPER FUNCTIONS
# ============================================================

def extract_video_id(url: str) -> str:
    """
    Extract the YouTube video ID from a YouTube URL.
    """

    pattern = (
        r"(?:https?://)?(?:www\.)?"
        r"(?:youtube\.com/(?:watch\?v=|embed/|shorts/|live/)|youtu\.be/)"
        r"([a-zA-Z0-9_-]{11})"
    )

    match = re.search(pattern, url)

    if not match:
        raise ValueError("Could not extract a valid YouTube video ID.")

    return match.group(1)


def fetch_transcript(video_id: str):
    """
    Fetch transcript from YouTube.
    """

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
    """
    Convert transcript into LangChain Documents
    and split them into smaller chunks.
    """

    full_transcript = " ".join(
        item["text"] for item in transcript_data
    )

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
                metadata={
                    "chunk_id": i
                }
            )
        )

    return documents


def create_vector_store(documents):
    """
    Create embeddings and store documents in ChromaDB.
    """

    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    vector_store = Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        persist_directory=str(CHROMA_DIR),
    )

    return vector_store


def create_rag_chain(retriever):
    """
    Create the Gemini RAG chain.
    """

    system_prompt = """
    You are an intelligent YouTube Video Assistant.

    Answer the user's question ONLY using the transcript
    context provided below.

    Rules:

    1. Answer only from the transcript context.
    2. Do not make up information.
    3. If the answer is not present in the transcript,
       say:
       "I couldn't find that information in the video transcript."
    4. Keep answers clear and concise.
    5. You may combine information from multiple chunks.

    Transcript Context:
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
        return "\n\n---\n\n".join(
            doc.page_content for doc in docs
        )

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


# ============================================================
# 4. SESSION STATE
# ============================================================

if "processed" not in st.session_state:
    st.session_state.processed = False

if "video_id" not in st.session_state:
    st.session_state.video_id = None

if "chain" not in st.session_state:
    st.session_state.chain = None

if "messages" not in st.session_state:
    st.session_state.messages = []


# ============================================================
# 5. HEADER
# ============================================================

st.title("🎥 YouTube RAG Chatbot")

st.caption(
    "Ask questions about a YouTube video using Retrieval-Augmented Generation."
)


# ============================================================
# 6. VIDEO SETUP
# ============================================================

with st.sidebar:

    st.header("🎬 Video Setup")

    youtube_url = st.text_input(
        "YouTube URL",
        placeholder="https://www.youtube.com/watch?v=..."
    )

    process_video = st.button(
        "Process Video",
        use_container_width=True
    )


# ============================================================
# 7. PROCESS VIDEO
# ============================================================

if process_video:

    if not youtube_url:
        st.error("Please enter a YouTube URL.")

    else:

        try:

            video_id = extract_video_id(youtube_url)

            with st.spinner("Fetching transcript..."):

                transcript_data = fetch_transcript(video_id)

            st.success(
                f"Transcript fetched successfully: "
                f"{len(transcript_data)} transcript segments"
            )

            with st.spinner("Creating chunks..."):

                documents = create_chunks(transcript_data)

            st.info(
                f"{len(documents)} chunks created."
            )

            # Remove previous Chroma database
            if CHROMA_DIR.exists():
                shutil.rmtree(CHROMA_DIR)

            CHROMA_DIR.mkdir(exist_ok=True)

            with st.spinner("Creating embeddings and indexing..."):

                vector_store = create_vector_store(documents)

            st.success(
                "Embeddings created and stored in ChromaDB."
            )

            retriever = vector_store.as_retriever(
                search_kwargs={"k": 3}
            )

            st.session_state.chain = create_rag_chain(
                retriever
            )

            st.session_state.video_id = video_id
            st.session_state.processed = True
            st.session_state.messages = []

            st.success("🎉 Video is ready for questions!")

        except Exception as e:

            st.error(
                f"Failed to process video:\n\n{str(e)}"
            )


# ============================================================
# 8. DISPLAY VIDEO
# ============================================================

if st.session_state.processed:

    video_url = (
        f"https://www.youtube.com/watch?v="
        f"{st.session_state.video_id}"
    )

    st.subheader("📺 Video")

    st.video(video_url)

    st.divider()


# ============================================================
# 9. CHAT
# ============================================================

st.subheader("💬 Ask about this video")


if not st.session_state.processed:

    st.info(
        "Enter a YouTube URL from the sidebar and "
        "click **Process Video** to begin."
    )

else:

    # Display previous messages
    for message in st.session_state.messages:

        with st.chat_message(message["role"]):

            st.markdown(message["content"])


    # Chat input
    question = st.chat_input(
        "Ask a question about the video..."
    )

    if question:

        # Display user message
        st.session_state.messages.append(
            {
                "role": "user",
                "content": question
            }
        )

        with st.chat_message("user"):
            st.markdown(question)

        # Generate answer
        with st.chat_message("assistant"):

            with st.spinner("Thinking..."):

                try:

                    answer = st.session_state.chain.invoke(
                        question
                    )

                    st.markdown(answer)

                    st.session_state.messages.append(
                        {
                            "role": "assistant",
                            "content": answer
                        }
                    )

                except Exception as e:

                    error_message = (
                        f"Sorry, something went wrong: {str(e)}"
                    )

                    st.error(error_message)

                    st.session_state.messages.append(
                        {
                            "role": "assistant",
                            "content": error_message
                        }
                    )