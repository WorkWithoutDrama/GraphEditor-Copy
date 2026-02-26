"""Provider adapters: build kwargs for Ollama and Gemini from settings."""
from app.llm.providers.gemini import gemini_kwargs
from app.llm.providers.ollama import ollama_kwargs

__all__ = ["ollama_kwargs", "gemini_kwargs"]
