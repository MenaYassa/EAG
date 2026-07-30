"""AI Capabilities for EAG."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True, kw_only=True)
class AICapabilities:
    """Describes what a model can do (binary capabilities)."""

    supports_text: bool = True
    supports_code: bool = False
    supports_images: bool = False
    supports_audio: bool = False
    supports_video: bool = False
    supports_embeddings: bool = False
    supports_streaming: bool = False
    supports_function_calls: bool = False
    supports_json_schema: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.supports_text, bool):
            raise TypeError("supports_text must be a bool")
        if not isinstance(self.supports_code, bool):
            raise TypeError("supports_code must be a bool")
        if not isinstance(self.supports_images, bool):
            raise TypeError("supports_images must be a bool")
        if not isinstance(self.supports_audio, bool):
            raise TypeError("supports_audio must be a bool")
        if not isinstance(self.supports_video, bool):
            raise TypeError("supports_video must be a bool")
        if not isinstance(self.supports_embeddings, bool):
            raise TypeError("supports_embeddings must be a bool")
        if not isinstance(self.supports_streaming, bool):
            raise TypeError("supports_streaming must be a bool")
        if not isinstance(self.supports_function_calls, bool):
            raise TypeError("supports_function_calls must be a bool")
        if not isinstance(self.supports_json_schema, bool):
            raise TypeError("supports_json_schema must be a bool")
