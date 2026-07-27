"""AI Intelligence errors for EAG."""


class IntelligenceError(Exception):
    """Base error for all AI intelligence failures."""


class ProviderError(IntelligenceError):
    """Raised when a provider operation fails."""


class ModelNotFoundError(IntelligenceError):
    """Raised when a specific model is not found."""


class ProviderNotFoundError(IntelligenceError):
    """Raised when a specific provider is not found."""


class RoutingPolicyError(IntelligenceError):
    """Raised when a routing policy is invalid or cannot be applied."""


class SelectionError(IntelligenceError):
    """Raised when model selection fails."""

class NoMatchingModelError(IntelligenceError):
  """Raised when no available model satisfies the requirements."""
  def __init__(self, message: str, reasons: list[str] | None = None) -> None:
      super().__init__(message)
      self.reasons = reasons or []