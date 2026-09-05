from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

def chunk_transcript(transcript: list[dict] | str) -> list[Document]:
    """
    Chunk the transcript text into LangChain Document objects.
    Accepts either a list of snippets (with a 'text' key) or a raw string.
    """
    if isinstance(transcript, list):
        full_transcript = " ".join(
            snippet["text"] if isinstance(snippet, dict) else snippet.text
            for snippet in transcript
        )
    elif isinstance(transcript, str):
        full_transcript = transcript
    else:
        raise TypeError("Transcript must be a list of snippets or a string.")
        
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=600,
        chunk_overlap=100
    )
    
    chunks = splitter.split_text(full_transcript)
    
    documents = []
    for i, chunk in enumerate(chunks):
        documents.append(
            Document(
                page_content=chunk,
                metadata={
                    "chunk_id": i
                }
            )
        )
        
    return documents
