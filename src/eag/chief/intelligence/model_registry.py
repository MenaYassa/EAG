"""Model registry for EAG Chief Engineer."""

from eag.chief.intelligence.enums import ModelStatus
from eag.chief.intelligence.models import ModelProfile


class ModelRegistry:
    """Discovers and manages available AI models."""

    def __init__(self) -> None:
        self._models: dict[str, ModelProfile] = {}

    def register(self, model: ModelProfile) -> None:
        if model.id in self._models:
            raise ValueError(f"Model '{model.id}' is already registered.")
        self._models[model.id] = model

    def unregister(self, model_id: str) -> bool:
        return self._models.pop(model_id, None) is not None

    def find(self, model_id: str) -> ModelProfile:
        if model_id not in self._models:
            raise ValueError(f"Model '{model_id}' not found.")
        return self._models[model_id]

    def list(self) -> tuple[ModelProfile, ...]:
        return tuple(sorted(self._models.values(), key=lambda m: m.id))

    def available(self) -> tuple[ModelProfile, ...]:
        """Returns only available models, sorted by ID for determinism."""
        return tuple(m for m in self.list() if m.status == ModelStatus.AVAILABLE)

    def by_provider(self, provider_id: str) -> tuple[ModelProfile, ...]:
        return tuple(m for m in self.available() if m.provider_id == provider_id)

    def search(self, query: str) -> tuple[ModelProfile, ...]:
        query = query.lower()
        return tuple(m for m in self.list() if query in m.name.lower() or query in m.id.lower())