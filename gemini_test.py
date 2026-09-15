from app.core.config import GEMINI_API_KEY
from google import genai

api_key = GEMINI_API_KEY

client = genai.Client(api_key=api_key)

response = client.models.generate_content(
    model="gemini-3.6-flash",
    contents="Say hello and confirm you are working."
)

print(response.text)