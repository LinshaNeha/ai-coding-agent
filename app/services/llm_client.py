from abc import ABC, abstractmethod
from google import genai
from app.core.config import GEMINI_API_KEY


class LLMClient(ABC):
    @abstractmethod
    def generate(self, prompt: str) -> dict:
        """Returns a dict with keys: text, input_tokens, output_tokens"""
        pass


class GeminiClient(LLMClient):
    def __init__(self, model: str = "gemini-3.6-flash"):
        self.client = genai.Client(api_key=GEMINI_API_KEY)
        self.model = model

    def generate(self, prompt: str) -> dict:
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt
        )
        usage = getattr(response, "usage_metadata", None)
        return {
            "text": response.text,
            "input_tokens": getattr(usage, "prompt_token_count", 0) if usage else 0,
            "output_tokens": getattr(usage, "candidates_token_count", 0) if usage else 0,
        }


class ClaudeClient(LLMClient):
    def __init__(self, model: str = "claude-sonnet-4-6"):
        self.model = model
        # TODO: wire up Anthropic SDK when budget allows

    def generate(self, prompt: str) -> dict:
        raise NotImplementedError("Claude client not yet implemented")


class OpenAIClient(LLMClient):
    def __init__(self, model: str = "gpt-4o"):
        self.model = model
        # TODO: wire up OpenAI SDK when budget allows

    def generate(self, prompt: str) -> dict:
        raise NotImplementedError("OpenAI client not yet implemented")


def get_llm_client(provider: str = "gemini") -> LLMClient:
    if provider == "gemini":
        return GeminiClient()
    elif provider == "claude":
        return ClaudeClient()
    elif provider == "openai":
        return OpenAIClient()
    else:
        raise ValueError(f"Unknown provider: {provider}")