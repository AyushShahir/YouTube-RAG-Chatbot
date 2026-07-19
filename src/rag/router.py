from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI
# pyrefly: ignore [missing-import]
from src.utils.helper import load_env

load_env()

# ---------- 1. The classifier ----------

CLASSIFIER_PROMPT = """
You are a router that decides how to answer a user's question about a YouTube video.

Video Title: {title}
Video Channel: {channel}

Below are the most relevant chunks retrieved from the video's transcript:
---
{context}
---

The user asked: "{question}"

Decide which ONE category best fits the question:

- IN_VIDEO: The transcript chunks above actually contain the answer.
- RELATED_EXTERNAL: The transcript does NOT contain the answer, but the question
  is still about this video's subject, creator, or topic (e.g. general background
  info about the person/topic in the video, not covered in the transcript itself).
- UNRELATED: The question has nothing to do with this video's subject at all.

Reply with exactly ONE word and nothing else: IN_VIDEO, RELATED_EXTERNAL, or UNRELATED.
"""

def classify_question(question: str, context: str, video_metadata: dict) -> str:
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)
    prompt = ChatPromptTemplate.from_template(CLASSIFIER_PROMPT)
    chain = prompt | llm | StrOutputParser()

    raw_label = chain.invoke({
        "title": video_metadata.get("title", "Unknown"),
        "channel": video_metadata.get("channel", "Unknown"),
        "question": question,
        "context": context
    })

    label = raw_label.strip().upper()
    if "IN_VIDEO" in label:
        return "IN_VIDEO"
    elif "RELATED_EXTERNAL" in label:
        return "RELATED_EXTERNAL"
    else:
        return "UNRELATED"


# ---------- 2. The "general knowledge" chain (for RELATED_EXTERNAL) ----------

GENERAL_SYSTEM_PROMPT = """
You are a helpful assistant answering a question related to a YouTube video's subject.

The video is titled "{title}" by {channel}.

The user's question is NOT answered in the video transcript, but it IS related
to the subject of this video. Answer using your own general knowledge.
Be accurate and concise. If you're not confident, say so honestly.

Always start your answer with: "This isn't covered in the video, but here's what I know:"
"""

def create_general_chain(video_metadata: dict):
    prompt = ChatPromptTemplate.from_messages([
        ("system", GENERAL_SYSTEM_PROMPT),
        ("human", "{question}")
    ])
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.3)

    chain = (
        prompt.partial(
            title=video_metadata.get("title", "Unknown"),
            channel=video_metadata.get("channel", "Unknown")
        )
        | llm
        | StrOutputParser()
    )
    return chain


# ---------- 3. The router that ties it all together ----------

UNRELATED_RESPONSE = (
    "That doesn't seem related to this video. "
    "I can only answer questions about this video's content or its subject."
)

def get_answer(question: str, retriever, video_metadata: dict, rag_chain):
    """
    Classifies the question and routes it to the right chain.
    Returns (answer_text, source_label) so the UI can show where the answer came from.
    """
    docs = retriever.invoke(question)
    context = "\n\n---\n\n".join(doc.page_content for doc in docs)

    label = classify_question(question, context, video_metadata)

    if label == "IN_VIDEO":
        answer = rag_chain.invoke(question)
        source = "📄 From the video"
    elif label == "RELATED_EXTERNAL":
        general_chain = create_general_chain(video_metadata)
        answer = general_chain.invoke({"question": question})
        source = "🌐 General knowledge"
    else:
        answer = UNRELATED_RESPONSE
        source = "❌ Not related to video"

    return answer, source