"""Validation domain models for EAG."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Any


class ValidationSeverity(StrEnum):
    """Severity levels for validation issues."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ValidationCategory(StrEnum):
    """Categories of validation rules."""
    STRUCTURE = "structure"
    DEPENDENCY = "dependency"
    SAFETY = "safety"
    RISK = "risk"
    EXECUTION = "execution"


@dataclass(frozen=True, slots=True, kw_only=True)
class ValidationIssue:
    """An immutable representation of a validation finding."""
    category: ValidationCategory
    severity: ValidationSeverity
    message: str
    affected_tasks: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict, hash=False)

    def __post_init__(self) -> None:
        if not isinstance(self.category, ValidationCategory):
            raise TypeError("category must be a ValidationCategory")
        if not isinstance(self.severity, ValidationSeverity):
            raise TypeError("severity must be a ValidationSeverity")
        if not isinstance(self.message, str) or not self.message.strip():
            raise ValueError("message cannot be empty")
        if not isinstance(self.affected_tasks, tuple):
            raise TypeError("affected_tasks must be a tuple")
        if not isinstance(self.metadata, Mapping):
            raise TypeError("metadata must be a Mapping")
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))


@dataclass(frozen=True, slots=True, kw_only=True)
class EngineeringPlanValidationResult:
    """The final artifact produced by the PlanValidator."""
    valid: bool
    issues: tuple[ValidationIssue, ...] = ()
    warnings: int = 0
    errors: int = 0
    critical: int = 0
    requires_approval: bool = False
    summary: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.valid, bool):
            raise TypeError("valid must be a bool")
        if not isinstance(self.issues, tuple):
            raise TypeError("issues must be a tuple")
        for field_name in ["warnings", "errors", "critical"]:
            val = getattr(self, field_name)
            if not isinstance(val, int) or val < 0:
                raise ValueError(f"{field_name} must be a non-negative integer")
        if not isinstance(self.requires_approval, bool):
            raise TypeError("requires_approval must be a bool")
        if not isinstance(self.summary, str):
            raise TypeError("summary must be a str")