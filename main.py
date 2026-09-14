import os
from dotenv import load_dotenv
from google import genai
from fastapi import FastAPI
from pydantic import BaseModel

# Load the API key from .env
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

app = FastAPI()


class ChatRequest(BaseModel):
    question: str


@app.get("/")
def read_root():
    return {"message": "Hello, AI Coding Agent is alive!"}


@app.post("/chat")
def chat(request: ChatRequest):
    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=request.question
    )
    return {"answer": response.text}