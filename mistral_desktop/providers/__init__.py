from .base import ChatChunk, ChatProvider, ProviderError
from .openai_compat import OpenAICompatProvider

MISTRAL_BASE_URL = "https://api.mistral.ai/v1"
HF_BASE_URL = "https://router.huggingface.co/v1"


def mistral_provider(api_key: str) -> OpenAICompatProvider:
    return OpenAICompatProvider(MISTRAL_BASE_URL, api_key, name="Mistral")


def huggingface_provider(token: str) -> OpenAICompatProvider:
    return OpenAICompatProvider(HF_BASE_URL, token, name="Hugging Face")
