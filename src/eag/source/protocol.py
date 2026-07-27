"""Source provider protocol for EAG."""

from pathlib import Path
from typing import Protocol, runtime_checkable

from eag.source.models import Diagnostic, Language, SourceDocument


@runtime_checkable
class SourceProvider(Protocol):
    """The contract for a language source provider."""

    @property
    def language(self) -> Language: ...

    def supports(self, path: Path) -> bool: ...

    def parse(self, path: Path, content: str) -> SourceDocument: ...

    def validate(self, document: SourceDocument) -> tuple[Diagnostic, ...]: ...
