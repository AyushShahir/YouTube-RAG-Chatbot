from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_google_genai import ChatGoogleGenerativeAI
from src.utils.helper import load_env

# Ensure environment variables are loaded (for GOOGLE_API_KEY)
load_env()

# Helper function: Combine retrieved chunks into one context string
def format_docs(docs):
    return "\n\n---\n\n".join(doc.page_content for doc in docs)

SYSTEM_PROMPT = """
You are an intelligent YouTube Video Assistant.

Your job is to answer the user's question ONLY using the transcript context provided below.

Rules:
1. Answer only from the transcript context.
2. Do not make up information.
3. If the answer is not present in the transcript, reply:
   "I couldn't find that information in the video transcript."
4. Keep answers clear and concise.
5. If appropriate, summarize information from multiple transcript chunks.

Transcript Context:
{context}
"""

def create_rag_chain(retriever):
    """
    Create and return the RAG chain using the retriever and ChatGoogleGenerativeAI (Gemini).
    """
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            ("human", "{question}")
        ]
    )
    
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0
    )
    
    chain = (
        {
            "context": retriever | format_docs,
            "question": RunnablePassthrough()
        }
        | prompt
        | llm
        | StrOutputParser()
    )
    
    return chain

def ask_question(chain, question: str) -> str:
    """
    Invoke the RAG chain with the given question.
    """
    return chain.invoke(question)
