from app.services.ai.providers.openai_compatible import OpenAICompatibleProvider

class ModelRouter:
    """Provider-independent entry point. Add provider adapters here as the platform grows."""
    def __init__(self):
        self.providers = {
            "openai_compatible": OpenAICompatibleProvider(),
        }

    def get_provider(self, provider_name: str | None = None):
        name = provider_name or "openai_compatible"
        provider = self.providers.get(name)
        if not provider:
            raise ValueError(f"Unsupported AI provider: {name}")
        return provider

model_router = ModelRouter()
