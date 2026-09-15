from fastapi import Header, HTTPException
from app.core.config import API_KEY


def verify_api_key(x_api_key: str = Header(None)):
    """
    FastAPI dependency that checks for a valid X-API-Key header.
    Raises 401 if missing or incorrect.
    """
    if not API_KEY:
        # No key configured on the server side — auth is effectively disabled.
        # (Useful for local dev; you'd want this to fail loudly in production.)
        return

    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")