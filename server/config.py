import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from server/.env
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

class Config:
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY")
    DATABASE_URL = os.getenv("DATABASE_URL")
