import streamlit as st
import validators
import streamlit.components.v1 as components

# pyrefly: ignore [missing-import]
from src.utils.helper import load_env, ensure_dirs
# pyrefly: ignore [missing-import]
from src.youtube.transcript import fetch_transcript, extract_video_id, fetch_video_metadata
# pyrefly: ignore [missing-import]
from src.rag.chunking import chunk_transcript
# pyrefly: ignore [missing-import]
from src.rag.embeddings import create_vector_store
# pyrefly: ignore [missing-import]
from src.rag.retriever import load_retriever
# pyrefly: ignore [missing-import]
from src.rag.chain import create_rag_chain, ask_question
# pyrefly: ignore [missing-import]
from src.rag.router import get_answer

# Load environment variables on app startup
load_env()
# Ensure necessary directories exist
ensure_dirs()



# Set up page configurations
st.set_page_config(
    page_title="YouTube RAG Chatbot",
    page_icon="🎥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inject custom CSS for premium design and aesthetics
st.markdown("""
<style>
    /* Global fonts and background */
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap');
    
    html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
        background-color: var(--st-background-color) !important;
        font-family: 'Plus Jakarta Sans', sans-serif;
        color: var(--st-text-color) !important;
    }
    
    /* Title styling */
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Outfit', sans-serif;
        color: var(--st-text-color) !important;
    }

    /* Style the sidebar */
    [data-testid="stSidebar"] {
        background-color: var(--st-secondary-background-color) !important;
        border-right: 1px solid rgba(128, 128, 128, 0.15) !important;
    }
    
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] div {
        color: var(--st-text-color) !important;
    }
    
    /* Styled container inside sidebar */
    [data-testid="stSidebar"] div[data-testid="stVerticalBlockBorderDiv"] {
        background-color: var(--st-background-color) !important;
        border: 1px solid rgba(128, 128, 128, 0.2) !important;
        border-radius: 12px !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05) !important;
        padding: 16px !important;
    }

    /* Sidebar text input styling */
    [data-testid="stSidebar"] div[data-testid="stTextInput"] input {
        background-color: var(--st-background-color) !important;
        border: 1px solid rgba(128, 128, 128, 0.3) !important;
        color: var(--st-text-color) !important;
        border-radius: 8px !important;
    }
    [data-testid="stSidebar"] div[data-testid="stTextInput"] input:focus {
        border-color: var(--st-primary-color) !important;
        box-shadow: 0 0 0 2px rgba(128, 128, 128, 0.1) !important;
    }

    /* Custom button styling (primary buttons like Process Video) */
    div.stButton > button[kind="primary"],
    div.stButton > button:not([kind="secondary"]) {
        background: linear-gradient(135deg, #ff4b4b 0%, #ff8a3d 100%) !important;
        color: #ffffff !important;
        border: none !important;
        padding: 0.75rem 2rem !important;
        font-weight: 600 !important;
        border-radius: 10px !important;
        width: 100% !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        box-shadow: 0 4px 15px rgba(255, 75, 75, 0.2) !important;
        text-transform: uppercase;
        font-size: 0.85rem;
        letter-spacing: 0.5px;
    }
    
    div.stButton > button:not([kind="secondary"]):hover {
        background: linear-gradient(135deg, #ff6262 0%, #ff9e59 100%) !important;
        box-shadow: 0 6px 20px rgba(255, 75, 75, 0.35) !important;
        transform: translateY(-1px) !important;
        color: #ffffff !important;
    }

    /* Hide borders of the main container inside chat area so it's clean and cardless */
    [data-testid="stAppViewContainer"] [data-testid="stMain"] div[data-testid="stVerticalBlockBorderDiv"] {
        background-color: transparent !important;
        border: none !important;
        box-shadow: none !important;
        padding: 0px !important;
    }

    /* Placeholder centering inside Chat container */
    .placeholder-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        flex-grow: 1;
        color: var(--st-text-color) !important;
        opacity: 0.8 !important;
        text-align: center;
        padding: 80px 20px;
    }
    
    .placeholder-icon {
        font-size: 3.5rem;
        margin-bottom: 1rem;
        opacity: 0.5;
        animation: pulse 2s infinite ease-in-out;
    }
    
    @keyframes pulse {
        0%, 100% { opacity: 0.4; transform: scale(1); }
        50% { opacity: 0.7; transform: scale(1.05); }
    }

    /* Reset Streamlit default chat message container styles */
    [data-testid="stChatMessage"] {
        background-color: transparent !important;
        border: none !important;
        padding: 16px 0px !important;
        width: 100% !important;
        display: flex !important;
    }
    
    [data-testid="stChatMessageContent"] {
        padding: 12px 18px !important;
        box-shadow: none !important;
        display: inline-block !important;
        width: auto !important;
    }

    /* Target User Chat Bubble (Right Aligned) */
    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
        flex-direction: row-reverse !important;
    }
    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) [data-testid="stChatMessageContent"] {
        background-color: var(--st-secondary-background-color) !important;
        border: 1px solid rgba(128, 128, 128, 0.15) !important;
        max-width: 70% !important;
        border-radius: 20px !important;
        margin-right: 12px !important;
        margin-left: 0px !important;
        text-align: left !important;
    }
    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) [data-testid="stChatMessageContent"] p,
    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) [data-testid="stChatMessageContent"] span,
    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) [data-testid="stChatMessageContent"] div {
        color: var(--st-text-color) !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-size: 0.95rem !important;
        line-height: 1.6 !important;
    }

    /* Target Assistant Chat Bubble (Left Aligned - plain text on bg like ChatGPT) */
    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) {
        flex-direction: row !important;
    }
    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) [data-testid="stChatMessageContent"] {
        background-color: transparent !important;
        border: none !important;
        max-width: 80% !important;
        border-radius: 0px !important;
        margin-left: 12px !important;
        margin-right: 0px !important;
    }
    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) [data-testid="stChatMessageContent"] p,
    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) [data-testid="stChatMessageContent"] span,
    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) [data-testid="stChatMessageContent"] div {
        color: var(--st-text-color) !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-size: 0.95rem !important;
        line-height: 1.6 !important;
    }

    /* Video metadata card */
    .video-meta-card {
        margin-top: 16px;
        padding: 20px;
        border-radius: 14px;
        background-color: var(--st-secondary-background-color);
        border: 1px solid rgba(128, 128, 128, 0.15);
    }
    
    .video-meta-title {
        font-family: 'Outfit', sans-serif !important;
        font-weight: 600 !important;
        font-size: 1.15rem !important;
        color: var(--st-text-color) !important;
        margin-bottom: 15px !important;
        line-height: 1.4 !important;
    }
    
    .video-meta-grid {
        display: grid !important;
        grid-template-columns: 1fr 1fr !important;
        gap: 12px !important;
    }
    
    .video-meta-item {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-size: 0.9rem !important;
        color: var(--st-text-color) !important;
        opacity: 0.85 !important;
    }

    /* Gemini-style empty state */
    .gemini-empty-state {
        text-align: center;
        padding: 40px 20px 20px 20px;
        color: var(--st-text-color);
    }
    .gemini-empty-state .sparkle {
        font-size: 1.8rem;
        display: block;
        margin-bottom: 12px;
    }
    .gemini-empty-state .greeting {
        font-size: 1.1rem;
        font-weight: 500;
        opacity: 0.85;
    }

    /* Suggestion chip buttons — secondary style, pill-shaped */
    button[kind="secondary"] {
        background: transparent !important;
        border: 1px solid rgba(128, 128, 128, 0.35) !important;
        color: var(--st-text-color) !important;
        border-radius: 999px !important;
        padding: 0.5rem 1.2rem !important;
        text-transform: none !important;
        font-weight: 500 !important;
        font-size: 0.85rem !important;
        box-shadow: none !important;
        width: auto !important;
    }
    button[kind="secondary"]:hover {
        border-color: var(--st-primary-color) !important;
        background: rgba(128, 128, 128, 0.08) !important;
    }

    /* Disclaimer footer text */
    .disclaimer-text {
        text-align: center;
        font-size: 0.75rem;
        opacity: 0.55;
        margin-top: 6px;
    }

    /* Hide visible scrollbars everywhere (scrolling still works internally, just not visible) */
    ::-webkit-scrollbar {
        width: 0px !important;
        height: 0px !important;
        background: transparent !important;
    }
    * {
        scrollbar-width: none !important;
        -ms-overflow-style: none !important;
    }

    /* Responsive adjustments for mobile screens */
    @media (max-width: 768px) {
        .stChatInput > div {
            width: 95% !important;
            max-width: 95% !important;
        }
    }
</style>
""", unsafe_allow_html=True)

# Left Sidebar for Video Setup
with st.sidebar:
    st.markdown(
        """
        <div style="padding: 10px 0; margin-bottom: 20px; border-bottom: 1px solid rgba(128, 128, 128, 0.2);">
            <h2 style="font-weight: 600; font-size: 1.3rem; color: var(--st-text-color); margin: 0; text-align: left; display: flex; align-items: center; gap: 10px;">
                <span>📁</span> <span>YouTube RAG Chatbot</span>
            </h2>
        </div>
        """, 
        unsafe_allow_html=True
    )
    st.markdown('<h3 style="margin-top:0; color:var(--st-text-color);">🎥 Video Setup</h3>', unsafe_allow_html=True)
    
    # Styled block container
    with st.container(border=True):
        youtube_url = st.text_input(
            "YouTube Video URL",
            placeholder="https://www.youtube.com/watch?v=...",
            help="Paste the link to the YouTube video you want to analyze."
        )
        
        process_btn = st.button("Process Video")
        
        # State handling real pipeline logic
        if process_btn:
            if not youtube_url:
                st.error("Please enter a YouTube URL.")
            elif not validators.url(youtube_url) or ("youtube.com" not in youtube_url and "youtu.be" not in youtube_url):
                st.error("Please enter a valid YouTube URL.")
            else:
                with st.spinner("⏳ Processing transcript..."):
                    try:
                        # 1. Fetch transcript
                        transcript_data = fetch_transcript(youtube_url)
                        # 2. Chunk transcript
                        docs = chunk_transcript(transcript_data)
                        # 3. Create embeddings & vector store
                        create_vector_store(docs)
                        # 4. Load retriever
                        retriever = load_retriever()
                        # 5. Create RAG chain
                        chain = create_rag_chain(retriever)
                        
                        # Fetch video metadata
                        metadata = fetch_video_metadata(youtube_url)
                        
                        # Store in session state
                        st.session_state["retriever"] = retriever
                        st.session_state["chain"] = chain
                        st.session_state["youtube_url"] = youtube_url
                        st.session_state["video_metadata"] = metadata
                        st.session_state["messages"] = []  # Clear chat history for new video
                        
                        st.success("Successfully processed video!")
                    except Exception as e:
                        st.error(f"Failed to process video: {str(e)}")

# Check if the entered YouTube URL is valid
is_valid_yt = False
video_id = None
if youtube_url:
    try:
        video_id = extract_video_id(youtube_url)
        is_valid_yt = True
    except Exception:
        pass

if not is_valid_yt:
    # Chat placeholder contents (when no valid YouTube URL is entered yet)
    st.markdown(
        """
        <div class="placeholder-container">
            <div class="placeholder-icon">🎥</div>
            <h4 style="color: var(--st-text-color); margin-bottom: 0.5rem; font-weight: 600; font-size: 1.5rem;">Ready to Ask Questions?</h4>
            <p style="max-width: 400px; font-size: 0.95rem; margin-top: 0; color: var(--st-text-color); opacity: 0.7; line-height: 1.6;">
                Once you enter a YouTube URL in the left sidebar, the video player will appear here. After processing, you can start asking questions.
            </p>
        </div>
        """, 
        unsafe_allow_html=True
    )
    st.chat_input("Ask anything about this video...", disabled=True)
else:
    # Side-by-side columns for Video player and Chat interface
    col1, col2 = st.columns([5, 5], gap="large")
    
    with col1:
        st.markdown('<h3 style="margin-top: 0; color: var(--st-text-color); display: flex; align-items: center; gap: 8px;"><span>📺</span> Video Player</h3>', unsafe_allow_html=True)
        st.video(f"https://www.youtube.com/watch?v={video_id}")
            
        # Display metadata only if this URL is processed and matches the current URL
        if "chain" in st.session_state and st.session_state.get("youtube_url") == youtube_url:
            metadata = st.session_state.get("video_metadata", {})
            if metadata:
                st.markdown(f"""
                <div class="video-meta-card">
                    <div class="video-meta-title">{metadata.get('title', 'YouTube Video')}</div>
                    <div class="video-meta-grid">
                        <div class="video-meta-item"><strong>👤 Channel:</strong> {metadata.get('channel', 'N/A')}</div>
                        <div class="video-meta-item"><strong>👁️ Views:</strong> {metadata.get('views', 'N/A')}</div>
                        <div class="video-meta-item"><strong>⏱️ Duration:</strong> {metadata.get('duration', 'N/A')}</div>
                        <div class="video-meta-item"><strong>📅 Published:</strong> {metadata.get('published', 'N/A')}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
    with col2:
        st.markdown(
            '<h3 style="margin-top: 0; color: var(--st-text-color); display: flex; align-items: center; gap: 8px;">'
            '<span>✨</span> Ask about this video</h3>',
            unsafe_allow_html=True
        )
        
        # If this URL has not been processed yet, or is different from the processed URL
        if "chain" not in st.session_state or st.session_state.get("youtube_url") != youtube_url:
            st.markdown(
                """
                <div class="placeholder-container" style="padding: 40px 10px;">
                    <div class="placeholder-icon" style="font-size: 2.5rem;">⚡</div>
                    <h4 style="color: var(--st-text-color); margin-bottom: 0.5rem; font-weight: 600; font-size: 1.25rem;">Process the Video to Chat</h4>
                    <p style="max-width: 320px; font-size: 0.9rem; margin-top: 0; color: var(--st-text-color); opacity: 0.7; line-height: 1.5;">
                        Click the <strong>"Process Video"</strong> button in the left sidebar to fetch the transcript, generate embeddings, and unlock the chat.
                    </p>
                </div>
                """, 
                unsafe_allow_html=True
            )
            st.chat_input("Ask anything about this video...", disabled=True)
        else:
            # Initialize messages list
            if "messages" not in st.session_state:
                st.session_state["messages"] = []

            # Fixed-height, internally-scrollable chat area. Only this scrolls —
            # st.chat_input below is automatically pinned to the bottom of the screen
            # by Streamlit itself, so it's always visible without extra CSS.
            chat_container = st.container(height=400, border=False)
            with chat_container:
                if not st.session_state["messages"]:
                    # Gemini-style empty state with suggestion chips
                    st.markdown(
                        """
                        <div class="gemini-empty-state">
                            <span class="sparkle">✨</span>
                            <div class="greeting">Curious about what you're watching? I'm here to help.</div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
                    chip_col1, chip_col2, chip_col3 = st.columns(3)
                    chips = ["Summarize the video", "Recommend related content", "What's the key takeaway?"]
                    for chip_col, chip_text in zip([chip_col1, chip_col2, chip_col3], chips):
                        with chip_col:
                            if st.button(chip_text, key=f"chip_{chip_text}", type="secondary", use_container_width=True):
                                st.session_state["messages"].append({"role": "user", "content": chip_text})
                                st.rerun()
                else:
                    # Render message log
                    for msg in st.session_state["messages"]:
                        avatar_emoji = "🙂" if msg["role"] == "user" else "✨"
                        with st.chat_message(msg["role"], avatar=avatar_emoji):
                            st.write(msg["content"])
                            if msg.get("source"):
                                st.caption(msg["source"])
                    # Invisible anchor — the auto-scroll script below targets this
                    st.markdown('<div id="chat-bottom-anchor"></div>', unsafe_allow_html=True)

            # Auto-scroll the chat container (not the page) to the newest message
            components.html(
                """
                <script>
                    var anchor = window.parent.document.getElementById('chat-bottom-anchor');
                    if (anchor) { anchor.scrollIntoView({behavior: 'smooth', block: 'end'}); }
                </script>
                """,
                height=0
            )

            # Check if the last message is from the user, and if so, call RAG
            if st.session_state["messages"] and st.session_state["messages"][-1]["role"] == "user":
                user_question = st.session_state["messages"][-1]["content"]
                with st.spinner("🤖 Thinking..."):
                    try:
                        chain = st.session_state["chain"]
                        retriever = st.session_state["retriever"]
                        metadata = st.session_state.get("video_metadata", {})
                        answer, source = get_answer(user_question, retriever, metadata, chain)
                        st.session_state["messages"].append(
                            {"role": "assistant", "content": answer, "source": source}
                        )
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error generating answer: {str(e)}")

            # This input is automatically docked to the bottom of the browser window
            # by Streamlit — no custom CSS needed for it to stay visible.
            prompt = st.chat_input("Ask anything about this video...")
            if prompt:
                st.session_state["messages"].append({"role": "user", "content": prompt})
                st.rerun()

            # Gemini-style disclaimer footer
            st.markdown(
                '<p class="disclaimer-text">AI can make mistakes, so double-check it.</p>',
                unsafe_allow_html=True
            )