import os
from dotenv import load_dotenv
from google import genai

# Load the API key from .env
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=api_key)

response = client.models.generate_content(
    model="gemini-3.6-flash",
    contents="Say hello and confirm you are working."
)

print(response.text)