import os
from dotenv import load_dotenv

# Path calculations relative to this file.
# This file lives at: src/utils/helper.py
# So the true project root is TWO levels up (src/utils -> src -> project root).
# This file lives at src/utils/helper.py, so true project root is two levels up from SRC_DIR
UTILS_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.dirname(UTILS_DIR)
PROJECT_ROOT = os.path.dirname(SRC_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
CHROMA_DIR = os.path.join(DATA_DIR, "chroma_db")

def load_env():
    """Load environment variables from the root .env file."""
    env_path = os.path.join(PROJECT_ROOT, ".env")
    if os.path.exists(env_path):
        load_dotenv(env_path)
    else:
        # Fallback to system env
        load_dotenv()

def get_chroma_dir():
    """Get the path to the ChromaDB storage directory."""
    return CHROMA_DIR

def ensure_dirs():
    """Ensure that the data and chroma directories exist."""
    os.makedirs(DATA_DIR, exist_ok=True)