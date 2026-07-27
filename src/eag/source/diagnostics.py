from dataclasses import dataclass
from typing import TYPE_CHECKING

from eag.source.state import AnalysisSeverity

if TYPE_CHECKING:
    from eag.source.models import SourceLocation


@dataclass(frozen=True, slots=True, kw_only=True)
class AnalysisDiagnostic:
    severity: AnalysisSeverity
    message: str
    location: "SourceLocation"
    code: str | None = None

    def __post_init__(self) -> None:
        from eag.source.models import SourceLocation

        if not isinstance(self.severity, AnalysisSeverity):
            raise TypeError("severity must be an AnalysisSeverity")
        if not isinstance(self.message, str) or not self.message.strip():
            raise ValueError("message cannot be empty")
        if not isinstance(self.location, SourceLocation):
            raise TypeError("location must be a SourceLocation")
        if self.code is not None and not isinstance(self.code, str):
            raise TypeError("code must be a string or None")
