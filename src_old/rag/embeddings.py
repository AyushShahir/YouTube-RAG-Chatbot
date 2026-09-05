import os
import shutil
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from src.utils.helper import get_chroma_dir

def create_vector_store(documents):
    """
    Generate embeddings for documents and store them in ChromaDB.
    Clears any existing data in the storage directory first to ensure clean
    database initialization for the new video.
    """
    persist_dir = get_chroma_dir()
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    
    # Attempt to clean up old database directory
    if os.path.exists(persist_dir):
        try:
            shutil.rmtree(persist_dir)
        except PermissionError:
            try:
                # If directory is locked by python, use collection deletion
                db = Chroma(
                    persist_directory=persist_dir,
                    embedding_function=embeddings
                )
                db.delete_collection()
            except Exception:
                pass
                
    vector_store = Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        persist_directory=persist_dir
    )
    
    return vector_store
