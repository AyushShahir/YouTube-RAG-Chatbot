from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from src.utils.helper import get_chroma_dir

def load_retriever():
    """
    Load a LangChain retriever from the persisted ChromaDB.
    """
    persist_dir = get_chroma_dir()
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    
    vector_store = Chroma(
        persist_directory=persist_dir,
        embedding_function=embeddings
    )
    
    return vector_store.as_retriever(search_kwargs={"k": 5})
