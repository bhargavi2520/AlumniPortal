import os
from dotenv import load_dotenv

# Load explicitly defined environment variables from .env
load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

def get_env_variable(name):
    """Retrieve an environment variable or raise an exception."""
    try:
        return os.environ[name]
    except KeyError:
        raise RuntimeError(f"Missing required environment variable: {name}. Please check your .env file.")

class Config:
    SECRET_KEY = get_env_variable("SECRET_KEY")
    db_url = get_env_variable("DATABASE_URL")
    if db_url.startswith("sqlite:///"):
        db_path = db_url.replace("sqlite:///", "")
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(BASE_DIR, db_path)}"
    else:
        SQLALCHEMY_DATABASE_URI = db_url

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Storage Path Configuration
    UPLOAD_FOLDER = os.path.join(BASE_DIR, get_env_variable("UPLOAD_FOLDER"))
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024  # 8 MB
    ALLOWED_EXTENSIONS = {"pdf", "doc", "docx"}
