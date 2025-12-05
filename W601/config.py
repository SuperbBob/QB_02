"""
Configuration settings for Excel Agent
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Base paths
BASE_DIR = Path(__file__).parent
UPLOAD_DIR = BASE_DIR / "uploads"
KNOWLEDGE_BASE_DIR = BASE_DIR / "knowledge_base"

# Create directories if they don't exist
UPLOAD_DIR.mkdir(exist_ok=True)
KNOWLEDGE_BASE_DIR.mkdir(exist_ok=True)

# LLM Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", None)

# Server Configuration
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 8000))

# Analysis Settings
MAX_ROWS_PREVIEW = 1000
MAX_CODE_EXECUTION_TIME = 30  # seconds

# Supported file extensions
SUPPORTED_EXTENSIONS = [".xlsx", ".xls", ".csv"]

