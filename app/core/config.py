import os
from pathlib import Path

def load_env():
    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    if not env_path.exists():
        return
    with open(env_path) as f:
        lines = f.readlines()
    for line in lines:
        clean = line.strip()
        if not clean or clean.startswith("#") or "=" not in clean:
            continue
        key, value = clean.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key not in os.environ:
            os.environ[key] = value

load_env()

DATABASE_URL = os.environ.get("DATABASE_URL")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
API_KEY = os.environ.get("API_KEY")
ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")