"""Sensitive-path exclusion and redaction for repository context assembly."""

from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from eag.repository.ignore import IgnoreEngine


@dataclass(frozen=True, slots=True, kw_only=True)
class SensitivityDecision:
    """A redacted policy result that never stores file content or host paths."""

    action: str
    reason: str
    repository_path: str

    def __post_init__(self) -> None:
        if self.action not in {"included", "redacted", "excluded"}:
            raise ValueError("action must be included, redacted, or excluded")
        relative = PurePosixPath(self.repository_path)
        if relative.is_absolute() or ".." in relative.parts or not relative.parts:
            raise ValueError("repository_path must be a relative repository path")


@dataclass(frozen=True, slots=True, kw_only=True)
class SanitizedContent:
    """Provider-safe content result with redaction accounting only."""

    content: str | None
    decision: SensitivityDecision
    redaction_count: int = 0


@dataclass(frozen=True, slots=True, kw_only=True)
class ContextSecurityPolicy:
    """Layered, fail-closed content safety policy for context assembly."""

    configured_sensitive_paths: frozenset[str] = field(default_factory=frozenset)
    max_file_bytes: int = 512_000
    policy_version: str = "1.0"

    _SENSITIVE_COMPONENTS = frozenset({".ssh", "secrets", "credentials", "credential"})
    _SENSITIVE_FILENAMES = frozenset(
        {
            ".env",
            ".npmrc",
            ".pypirc",
            "credentials",
            "credentials.json",
            "id_rsa",
            "id_dsa",
            "id_ecdsa",
            "id_ed25519",
            "known_hosts",
        }
    )
    _SENSITIVE_SUFFIXES = frozenset({".key", ".pem", ".p12", ".pfx", ".ppk", ".jks", ".crt"})
    _ASSIGNMENT_PATTERN = re.compile(
        r"(?im)(\b(?:api[_-]?key|access[_-]?token|auth[_-]?token|client[_-]?secret|"
        r"secret|password|passwd|private[_-]?key)\b\s*[:=]\s*)([^\s#;]+)"
    )
    _BEARER_PATTERN = re.compile(r"(?i)(\bBearer\s+)[A-Za-z0-9._~+/=-]{8,}")
    _AWS_KEY_PATTERN = re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")
    _GITHUB_TOKEN_PATTERN = re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b")

    def __post_init__(self) -> None:
        if self.max_file_bytes < 0:
            raise ValueError("max_file_bytes cannot be negative")
        if not self.policy_version.strip():
            raise ValueError("policy_version cannot be empty")

    def classify_path(self, path: Path, repository_root: Path) -> SensitivityDecision:
        """Classify a candidate path without reading its content or exposing its host path."""
        relative = self._relative_path(path, repository_root)
        if relative is None:
            return SensitivityDecision(
                action="excluded",
                reason="outside_repository",
                repository_path="__outside_repository__",
            )

        if any(IgnoreEngine().should_ignore(Path(part)) for part in PurePosixPath(relative).parts):
            return SensitivityDecision(action="excluded", reason="repository_ignore", repository_path=relative)

        lower_parts = tuple(part.lower() for part in PurePosixPath(relative).parts)
        lower_name = lower_parts[-1]
        if any(part in self._SENSITIVE_COMPONENTS for part in lower_parts[:-1]):
            return SensitivityDecision(action="excluded", reason="sensitive_directory", repository_path=relative)
        if lower_name in self._SENSITIVE_FILENAMES or lower_name.startswith(".env."):
            return SensitivityDecision(action="excluded", reason="sensitive_filename", repository_path=relative)
        if any(lower_name.endswith(suffix) for suffix in self._SENSITIVE_SUFFIXES):
            return SensitivityDecision(action="excluded", reason="sensitive_suffix", repository_path=relative)
        if any(fnmatch.fnmatch(relative, pattern) for pattern in self.configured_sensitive_paths):
            return SensitivityDecision(action="excluded", reason="configured_sensitive_path", repository_path=relative)
        return SensitivityDecision(action="included", reason="allowed_path", repository_path=relative)

    def read_sanitized(self, path: Path, repository_root: Path) -> SanitizedContent:
        """Read a safe text file and redact credentials; all unclassifiable content is excluded."""
        decision = self.classify_path(path, repository_root)
        if decision.action == "excluded":
            return SanitizedContent(content=None, decision=decision)
        try:
            data = path.read_bytes()
        except (OSError, ValueError):
            return SanitizedContent(
                content=None,
                decision=SensitivityDecision(
                    action="excluded", reason="unreadable_file", repository_path=decision.repository_path
                ),
            )
        if len(data) > self.max_file_bytes:
            return SanitizedContent(
                content=None,
                decision=SensitivityDecision(
                    action="excluded", reason="oversized_file", repository_path=decision.repository_path
                ),
            )
        if b"\x00" in data:
            return SanitizedContent(
                content=None,
                decision=SensitivityDecision(
                    action="excluded", reason="binary_file", repository_path=decision.repository_path
                ),
            )
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            return SanitizedContent(
                content=None,
                decision=SensitivityDecision(
                    action="excluded", reason="non_utf8_file", repository_path=decision.repository_path
                ),
            )
        redacted, count = self.redact_text(text)
        if count:
            return SanitizedContent(
                content=redacted,
                decision=SensitivityDecision(
                    action="redacted", reason="credential_pattern", repository_path=decision.repository_path
                ),
                redaction_count=count,
            )
        return SanitizedContent(content=text, decision=decision)

    def redact_text(self, text: str) -> tuple[str, int]:
        """Redact common credential/token values while retaining useful configuration keys."""
        count = 0

        def assignment_replacement(match: re.Match[str]) -> str:
            nonlocal count
            count += 1
            return f"{match.group(1)}[REDACTED]"

        redacted = self._ASSIGNMENT_PATTERN.sub(assignment_replacement, text)
        for pattern, replacement in (
            (self._BEARER_PATTERN, r"\1[REDACTED]"),
            (self._AWS_KEY_PATTERN, "[REDACTED_AWS_KEY]"),
            (self._GITHUB_TOKEN_PATTERN, "[REDACTED_GITHUB_TOKEN]"),
        ):
            redacted, matches = pattern.subn(replacement, redacted)
            count += matches
        return redacted, count

    @staticmethod
    def _relative_path(path: Path, repository_root: Path) -> str | None:
        try:
            relative = path.resolve().relative_to(repository_root.resolve())
        except (OSError, ValueError):
            return None
        posix = PurePosixPath(relative.as_posix())
        if posix.is_absolute() or ".." in posix.parts or not posix.parts:
            return None
        return posix.as_posix()
