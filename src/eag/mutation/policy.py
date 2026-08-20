"""Deterministic, fail-closed policy validation for untrusted mutation proposals."""

from __future__ import annotations

import stat
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from eag.context.sensitivity import ContextSecurityPolicy
from eag.mutation.errors import MutationPolicyError, MutationViolation, MutationViolationCode
from eag.mutation.models import (
    ChangeProposal,
    MutationOperation,
    ValidatedChangeProposal,
    _sha256_text,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class MutationPolicySettings:
    """Fixed, conservative first-slice limits for one text-file mutation."""

    max_content_bytes: int = 64_000
    max_target_bytes: int = 64_000
    policy_version: str = "1.0"

    def __post_init__(self) -> None:
        if self.max_content_bytes <= 0 or self.max_target_bytes <= 0:
            raise ValueError("mutation content limits must be positive")
        if not self.policy_version.strip():
            raise ValueError("policy_version cannot be empty")


class MutationPolicyValidator:
    """Validates a proposal without performing a mutation or exposing content in errors."""

    def __init__(
        self,
        *,
        settings: MutationPolicySettings | None = None,
        sensitivity_policy: ContextSecurityPolicy | None = None,
    ) -> None:
        self._settings = settings or MutationPolicySettings()
        self._sensitivity = sensitivity_policy or ContextSecurityPolicy(
            max_file_bytes=self._settings.max_target_bytes,
            policy_version=self._settings.policy_version,
        )

    @property
    def policy_version(self) -> str:
        return self._settings.policy_version

    def validate(self, proposal: ChangeProposal, workspace_root: Path) -> ValidatedChangeProposal:
        """Validate one proposal against filesystem state without writing anything."""
        root = workspace_root.resolve(strict=True)
        relative = self._validate_relative_path(proposal)
        target = self._resolve_safe_target(root, relative, proposal)
        self._validate_sensitive_path(target, root, proposal)
        self._validate_content(proposal)

        exists = target.exists()
        target_size = 0
        target_fingerprint: str | None = None
        if exists:
            self._validate_existing_target(target, proposal)
            data = target.read_bytes()
            target_size = len(data)
            if target_size > self._settings.max_target_bytes:
                self._reject(
                    MutationViolationCode.TARGET_TOO_LARGE,
                    "target file exceeds mutation size limit",
                    proposal,
                )
            if b"\x00" in data:
                self._reject(
                    MutationViolationCode.TARGET_NOT_REGULAR_FILE,
                    "binary target files are not supported",
                    proposal,
                )
            try:
                text = data.decode("utf-8")
            except UnicodeDecodeError:
                self._reject(
                    MutationViolationCode.TARGET_NOT_REGULAR_FILE,
                    "non-UTF-8 target files are not supported",
                    proposal,
                )
            target_fingerprint = _sha256_text(text)

        self._validate_operation_state(proposal, exists, target_fingerprint)
        return ValidatedChangeProposal(
            proposal=proposal,
            target_fingerprint=target_fingerprint,
            target_size=target_size,
            target_exists=exists,
            workspace_fingerprint=self.workspace_fingerprint(root),
        )

    def workspace_fingerprint(self, workspace_root: Path) -> str:
        """Compute a bounded root identity without scanning or exposing its host path."""
        root = workspace_root.resolve(strict=True)
        root_stat = root.stat()
        return _sha256_text(f"{root_stat.st_dev}:{root_stat.st_ino}")

    def _validate_relative_path(self, proposal: ChangeProposal) -> PurePosixPath:
        raw = proposal.target_path
        if Path(raw).is_absolute() or PurePosixPath(raw).is_absolute():
            self._reject(MutationViolationCode.ABSOLUTE_PATH, "absolute target paths are forbidden", proposal)
        path = PurePosixPath(raw)
        if not path.parts or any(part in {"", ".", ".."} for part in path.parts):
            self._reject(MutationViolationCode.PATH_TRAVERSAL, "target path traversal is forbidden", proposal)
        if "\x00" in raw or any("\\" in part for part in path.parts):
            self._reject(MutationViolationCode.MALFORMED_PROPOSAL, "target path is malformed", proposal)
        return path

    def _resolve_safe_target(
        self,
        root: Path,
        relative: PurePosixPath,
        proposal: ChangeProposal,
    ) -> Path:
        current = root
        for component in relative.parts[:-1]:
            current = current / component
            if not current.exists():
                self._reject(
                    MutationViolationCode.PARENT_MISSING,
                    "target parent directory does not exist",
                    proposal,
                )
            mode = current.lstat().st_mode
            if stat.S_ISLNK(mode):
                self._reject(MutationViolationCode.SYMLINK_PATH, "symlink parent is forbidden", proposal)
            if not stat.S_ISDIR(mode):
                self._reject(MutationViolationCode.PATH_ESCAPE, "target parent is not a directory", proposal)
        target = current / relative.parts[-1]
        if target.is_symlink():
            self._reject(MutationViolationCode.SYMLINK_PATH, "symlink target is forbidden", proposal)
        try:
            target.parent.resolve(strict=True).relative_to(root)
        except ValueError:
            self._reject(MutationViolationCode.PATH_ESCAPE, "target escapes workspace root", proposal)
        return target

    def _validate_sensitive_path(self, target: Path, root: Path, proposal: ChangeProposal) -> None:
        decision = self._sensitivity.classify_path(target, root)
        if decision.action == "excluded":
            self._reject(MutationViolationCode.SENSITIVE_PATH, "target is protected by sensitivity policy", proposal)

    def _validate_content(self, proposal: ChangeProposal) -> None:
        if proposal.content_bytes > self._settings.max_content_bytes:
            self._reject(MutationViolationCode.CONTENT_TOO_LARGE, "proposed content exceeds mutation size limit", proposal)
        _, redactions = self._sensitivity.redact_text(proposal.content)
        if redactions:
            self._reject(MutationViolationCode.SENSITIVE_CONTENT, "proposed content contains sensitive material", proposal)

    def _validate_existing_target(self, target: Path, proposal: ChangeProposal) -> None:
        mode = target.lstat().st_mode
        if not stat.S_ISREG(mode):
            self._reject(
                MutationViolationCode.TARGET_NOT_REGULAR_FILE,
                "target is not a regular file",
                proposal,
            )

    def _validate_operation_state(
        self,
        proposal: ChangeProposal,
        exists: bool,
        current_fingerprint: str | None,
    ) -> None:
        if proposal.operation is MutationOperation.CREATE_FILE:
            if exists:
                self._reject(
                    MutationViolationCode.CREATE_TARGET_EXISTS,
                    "create proposal target already exists",
                    proposal,
                )
            if proposal.precondition.expect_exists:
                self._reject(
                    MutationViolationCode.PRECONDITION_MISMATCH,
                    "create proposal requires absent-target precondition",
                    proposal,
                )
            return
        if proposal.operation is MutationOperation.MODIFY_FILE:
            if not exists:
                self._reject(
                    MutationViolationCode.MODIFY_TARGET_MISSING,
                    "modify proposal target is missing",
                    proposal,
                )
            if not proposal.precondition.expect_exists:
                self._reject(
                    MutationViolationCode.PRECONDITION_MISMATCH,
                    "modify proposal requires existing-target precondition",
                    proposal,
                )
            if current_fingerprint != proposal.precondition.expected_fingerprint:
                self._reject(
                    MutationViolationCode.PRECONDITION_STALE,
                    "target fingerprint does not match proposal precondition",
                    proposal,
                )
            return
        self._reject(MutationViolationCode.UNSUPPORTED_OPERATION, "operation is not supported", proposal)

    def _reject(
        self,
        code: MutationViolationCode,
        message: str,
        proposal: ChangeProposal,
    ) -> None:
        raise MutationPolicyError(
            MutationViolation(
                code=code,
                stage="mutation_policy",
                message=message,
                target_path=proposal.target_path,
                policy_version=self._settings.policy_version,
            )
        )
