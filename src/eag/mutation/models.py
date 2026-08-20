"""Immutable domain contracts for deterministic governed workspace mutation."""

from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Any

MUTATION_CONTRACT_VERSION = "1.0"


def _freeze_mapping(value: Mapping[str, Any], name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{name} must be a Mapping")
    return MappingProxyType(dict(value))


class MutationOperation(StrEnum):
    """The only file operations available in the first deterministic slice."""

    CREATE_FILE = "create_file"
    MODIFY_FILE = "modify_file"


class MutationRisk(StrEnum):
    """Declared risk level for an untrusted proposal."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class MutationAuthorizationState(StrEnum):
    """One-time authorization lifecycle states."""

    AUTHORIZED = "authorized"
    RESERVED = "reserved"
    CONSUMED = "consumed"
    REJECTED = "rejected"
    EXPIRED = "expired"


class MutationResult(StrEnum):
    """Terminal outcome recorded by a receipt."""

    COMPLETED = "completed"
    REJECTED = "rejected"
    FAILED = "failed"


@dataclass(frozen=True, slots=True, kw_only=True)
class MutationPrecondition:
    """State that must match before a mutation may be attempted."""

    expect_exists: bool
    expected_fingerprint: str | None = None

    def __post_init__(self) -> None:
        if self.expect_exists and not self.expected_fingerprint:
            raise ValueError("existing target requires expected_fingerprint")
        if not self.expect_exists and self.expected_fingerprint is not None:
            raise ValueError("absent target cannot declare expected_fingerprint")


@dataclass(frozen=True, slots=True, kw_only=True)
class MutationPostcondition:
    """Bounded deterministic postcondition; never a free-form test command."""

    expect_exists: bool = True
    expected_fingerprint: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class ChangeProposal:
    """Untrusted, non-executable proposal for exactly one bounded text-file mutation."""

    proposal_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    run_id: str
    decision_id: str
    target_path: str
    operation: MutationOperation
    content: str
    precondition: MutationPrecondition
    reason: str
    provenance_ids: tuple[str, ...]
    risk: MutationRisk = MutationRisk.MEDIUM
    authorization_metadata: Mapping[str, Any] = field(default_factory=dict, hash=False)
    expected_postcondition: MutationPostcondition = field(default_factory=MutationPostcondition)
    context_fingerprint: str = ""
    repository_snapshot_fingerprint: str = ""
    workspace_fingerprint: str = ""
    contract_version: str = MUTATION_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if not self.proposal_id.strip() or not self.run_id.strip() or not self.decision_id.strip():
            raise ValueError("proposal_id, run_id, and decision_id cannot be empty")
        if not self.target_path.strip():
            raise ValueError("target_path cannot be empty")
        if not self.reason.strip():
            raise ValueError("reason cannot be empty")
        if not isinstance(self.content, str):
            raise TypeError("content must be a string")
        if any(not item.strip() for item in self.provenance_ids):
            raise ValueError("provenance_ids cannot contain empty values")
        if len(set(self.provenance_ids)) != len(self.provenance_ids):
            raise ValueError("provenance_ids must be unique")
        if self.contract_version != MUTATION_CONTRACT_VERSION:
            raise ValueError("unsupported mutation contract version")
        object.__setattr__(
            self,
            "authorization_metadata",
            _freeze_mapping(self.authorization_metadata, "authorization_metadata"),
        )

    @property
    def content_fingerprint(self) -> str:
        return _sha256_text(self.content)

    @property
    def content_bytes(self) -> int:
        return len(self.content.encode("utf-8"))

    @property
    def digest(self) -> str:
        payload = {
            "proposal_id": self.proposal_id,
            "run_id": self.run_id,
            "decision_id": self.decision_id,
            "target_path": self.target_path,
            "operation": self.operation.value
            if isinstance(self.operation, MutationOperation)
            else str(self.operation),
            "content_fingerprint": self.content_fingerprint,
            "precondition": asdict(self.precondition),
            "reason": self.reason,
            "provenance_ids": self.provenance_ids,
            "risk": self.risk.value,
            "authorization_metadata": dict(self.authorization_metadata),
            "expected_postcondition": asdict(self.expected_postcondition),
            "context_fingerprint": self.context_fingerprint,
            "repository_snapshot_fingerprint": self.repository_snapshot_fingerprint,
            "workspace_fingerprint": self.workspace_fingerprint,
            "contract_version": self.contract_version,
        }
        return _sha256_payload(payload)


@dataclass(frozen=True, slots=True, kw_only=True)
class MutationAuthorization:
    """One-time, proposal-digest-bound authorization for one workspace operation."""

    authorization_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    proposal_id: str
    proposal_digest: str
    target_path: str
    operation: MutationOperation
    workspace_fingerprint: str
    repository_snapshot_fingerprint: str
    policy_version: str
    state: MutationAuthorizationState = MutationAuthorizationState.AUTHORIZED
    authorization_metadata: Mapping[str, Any] = field(default_factory=dict, hash=False)

    def __post_init__(self) -> None:
        if not self.proposal_id.strip() or not self.proposal_digest.strip():
            raise ValueError("proposal_id and proposal_digest cannot be empty")
        object.__setattr__(
            self,
            "authorization_metadata",
            _freeze_mapping(self.authorization_metadata, "authorization_metadata"),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class MutationReceipt:
    """Redacted immutable audit outcome for a mutation attempt; never stores file content."""

    mutation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    proposal_id: str
    run_id: str
    authorization_id: str | None
    target_path: str
    operation: MutationOperation
    result: MutationResult
    pre_fingerprint: str | None
    post_fingerprint: str | None
    bytes_before: int
    bytes_after: int
    bytes_changed: int
    authorization_state: MutationAuthorizationState | None
    policy_version: str
    failure_code: str | None = None
    failure_reason: str | None = None
    verification_passed: bool = False
    rollback_performed: bool = False
    contract_version: str = MUTATION_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if any(value < 0 for value in (self.bytes_before, self.bytes_after, self.bytes_changed)):
            raise ValueError("receipt byte counts cannot be negative")
        if self.result is MutationResult.COMPLETED and not self.verification_passed:
            raise ValueError("completed receipt requires successful verification")
        if self.failure_reason and len(self.failure_reason) > 512:
            raise ValueError("failure_reason must be sanitized and bounded")


@dataclass(frozen=True, slots=True, kw_only=True)
class ValidatedChangeProposal:
    """Internal policy-approved proposal state; absolute target stays inside the mutation layer."""

    proposal: ChangeProposal
    target_fingerprint: str | None
    target_size: int
    target_exists: bool
    workspace_fingerprint: str


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sha256_payload(value: Mapping[str, Any]) -> str:
    serialized = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
