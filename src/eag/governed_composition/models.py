"""Immutable, non-executing runtime composition provenance evidence."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum


class RuntimeCompositionError(ValueError):
    """Raised when runtime composition evidence is structurally invalid."""


class RuntimeCompositionDisposition(StrEnum):
    """Evidence-only outcome; it grants no runtime, session, permit, or invocation authority."""

    ATTESTED = "attested"


class RuntimeCompositionRejectionReason(StrEnum):
    """Typed refusals from the non-executing runtime composition boundary."""

    MISSING_ATTESTATION = "missing_attestation"
    ATTESTATION_UNKNOWN = "attestation_unknown"
    ATTESTATION_BINDING_MISMATCH = "attestation_binding_mismatch"
    STORE_UNAVAILABLE = "store_unavailable"
    STORE_CORRUPT = "store_corrupt"
    ATTESTATION_ID_DUPLICATE = "attestation_id_duplicate"
    ATTESTATION_ID_CONFLICT = "attestation_id_conflict"


def _require_non_empty(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RuntimeCompositionError(f"{field_name} cannot be empty")
    return value


def _require_digest(value: str, field_name: str) -> str:
    _require_non_empty(value, field_name)
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise RuntimeCompositionError(f"{field_name} must be a lowercase SHA-256 digest")
    return value


def _canonical_occurrence(value: datetime) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError("occurred_at must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise RuntimeCompositionError("occurred_at must be timezone-aware")
    return value.astimezone(UTC)


@dataclass(frozen=True, slots=True, kw_only=True)
class RuntimeComponentIdentity:
    """Redacted immutable identity declaration for one named G2.4.4 composition component."""

    role: str
    component_id: str
    version: str
    digest: str

    def __post_init__(self) -> None:
        for field_name in ("role", "component_id", "version"):
            object.__setattr__(self, field_name, _require_non_empty(getattr(self, field_name), field_name))
        object.__setattr__(self, "digest", _require_digest(self.digest, "digest"))

    def to_payload(self) -> dict[str, str]:
        return {
            "component_id": self.component_id,
            "digest": self.digest,
            "role": self.role,
            "version": self.version,
        }

    @classmethod
    def from_payload(cls, payload: object) -> RuntimeComponentIdentity:
        if not isinstance(payload, dict) or set(payload) != {"component_id", "digest", "role", "version"}:
            raise RuntimeCompositionError("invalid component identity payload")
        try:
            return cls(
                role=payload["role"],
                component_id=payload["component_id"],
                version=payload["version"],
                digest=payload["digest"],
            )
        except (KeyError, TypeError, RuntimeCompositionError) as error:
            raise RuntimeCompositionError("invalid component identity payload") from error


@dataclass(frozen=True, slots=True, kw_only=True)
class RuntimeDependencyBinding:
    """Redacted immutable declaration of a dependency relation among manifest component roles."""

    component_role: str
    dependency_role: str
    binding_digest: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "component_role", _require_non_empty(self.component_role, "component_role"))
        object.__setattr__(self, "dependency_role", _require_non_empty(self.dependency_role, "dependency_role"))
        object.__setattr__(self, "binding_digest", _require_digest(self.binding_digest, "binding_digest"))
        if self.component_role == self.dependency_role:
            raise RuntimeCompositionError("dependency binding cannot self-reference")

    def to_payload(self) -> dict[str, str]:
        return {
            "binding_digest": self.binding_digest,
            "component_role": self.component_role,
            "dependency_role": self.dependency_role,
        }

    @classmethod
    def from_payload(cls, payload: object) -> RuntimeDependencyBinding:
        if not isinstance(payload, dict) or set(payload) != {
            "binding_digest",
            "component_role",
            "dependency_role",
        }:
            raise RuntimeCompositionError("invalid dependency binding payload")
        try:
            return cls(
                component_role=payload["component_role"],
                dependency_role=payload["dependency_role"],
                binding_digest=payload["binding_digest"],
            )
        except (KeyError, TypeError, RuntimeCompositionError) as error:
            raise RuntimeCompositionError("invalid dependency binding payload") from error


@dataclass(frozen=True, slots=True, kw_only=True)
class RuntimeCompositionManifest:
    """Deterministic declared composition provenance; it contains no executable objects or credentials."""

    composition_id: str
    execution_id: str
    run_id: str
    runtime_id: str
    executor_identity: str
    component_identities: tuple[RuntimeComponentIdentity, ...]
    dependency_bindings: tuple[RuntimeDependencyBinding, ...]
    composition_policy_digest: str
    invocation_binding_digest: str
    contract_version: str = "g2.4.11"

    def __post_init__(self) -> None:
        for field_name in (
            "composition_id",
            "execution_id",
            "run_id",
            "runtime_id",
            "executor_identity",
            "contract_version",
        ):
            object.__setattr__(self, field_name, _require_non_empty(getattr(self, field_name), field_name))
        for field_name in ("composition_policy_digest", "invocation_binding_digest"):
            object.__setattr__(self, field_name, _require_digest(getattr(self, field_name), field_name))
        if not self.component_identities or any(
            not isinstance(component, RuntimeComponentIdentity) for component in self.component_identities
        ):
            raise RuntimeCompositionError("component_identities must contain at least one RuntimeComponentIdentity")
        roles = tuple(component.role for component in self.component_identities)
        if roles != tuple(sorted(roles)) or len(set(roles)) != len(roles):
            raise RuntimeCompositionError("component identities must be strictly ordered and role-unique")
        if any(not isinstance(binding, RuntimeDependencyBinding) for binding in self.dependency_bindings):
            raise TypeError("dependency_bindings must contain RuntimeDependencyBinding values")
        binding_keys = tuple(
            (binding.component_role, binding.dependency_role) for binding in self.dependency_bindings
        )
        if binding_keys != tuple(sorted(binding_keys)) or len(set(binding_keys)) != len(binding_keys):
            raise RuntimeCompositionError("dependency bindings must be strictly ordered and unique")
        role_set = set(roles)
        if any(
            binding.component_role not in role_set or binding.dependency_role not in role_set
            for binding in self.dependency_bindings
        ):
            raise RuntimeCompositionError("dependency bindings must reference declared component roles")

    @property
    def digest(self) -> str:
        return hashlib.sha256(
            json.dumps(self.to_payload(), separators=(",", ":"), sort_keys=True).encode()
        ).hexdigest()

    def to_payload(self) -> dict[str, object]:
        return {
            "component_identities": [component.to_payload() for component in self.component_identities],
            "composition_id": self.composition_id,
            "composition_policy_digest": self.composition_policy_digest,
            "contract_version": self.contract_version,
            "dependency_bindings": [binding.to_payload() for binding in self.dependency_bindings],
            "execution_id": self.execution_id,
            "executor_identity": self.executor_identity,
            "invocation_binding_digest": self.invocation_binding_digest,
            "run_id": self.run_id,
            "runtime_id": self.runtime_id,
        }

    @classmethod
    def from_payload(cls, payload: object) -> RuntimeCompositionManifest:
        required_fields = {
            "component_identities",
            "composition_id",
            "composition_policy_digest",
            "contract_version",
            "dependency_bindings",
            "execution_id",
            "executor_identity",
            "invocation_binding_digest",
            "run_id",
            "runtime_id",
        }
        if not isinstance(payload, dict) or set(payload) != required_fields:
            raise RuntimeCompositionError("runtime composition manifest has unexpected fields")
        try:
            components_payload = payload["component_identities"]
            dependencies_payload = payload["dependency_bindings"]
            if not isinstance(components_payload, list) or not isinstance(dependencies_payload, list):
                raise RuntimeCompositionError("manifest components and dependencies must be lists")
            return cls(
                composition_id=payload["composition_id"],
                execution_id=payload["execution_id"],
                run_id=payload["run_id"],
                runtime_id=payload["runtime_id"],
                executor_identity=payload["executor_identity"],
                component_identities=tuple(
                    RuntimeComponentIdentity.from_payload(component) for component in components_payload
                ),
                dependency_bindings=tuple(
                    RuntimeDependencyBinding.from_payload(binding) for binding in dependencies_payload
                ),
                composition_policy_digest=payload["composition_policy_digest"],
                invocation_binding_digest=payload["invocation_binding_digest"],
                contract_version=payload["contract_version"],
            )
        except (KeyError, TypeError, RuntimeCompositionError) as error:
            raise RuntimeCompositionError("invalid runtime composition manifest") from error


@dataclass(frozen=True, slots=True, kw_only=True)
class RuntimeCompositionAttestation:
    """Immutable durable composition evidence; it cannot construct or invoke the declared executor."""

    attestation_id: str
    manifest: RuntimeCompositionManifest
    occurred_at: datetime
    disposition: RuntimeCompositionDisposition
    binding_digest: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "attestation_id", _require_non_empty(self.attestation_id, "attestation_id"))
        if not isinstance(self.manifest, RuntimeCompositionManifest):
            raise TypeError("manifest must be a RuntimeCompositionManifest")
        object.__setattr__(self, "occurred_at", _canonical_occurrence(self.occurred_at))
        if self.disposition is not RuntimeCompositionDisposition.ATTESTED:
            raise RuntimeCompositionError("runtime composition attestation must be attested evidence")
        object.__setattr__(self, "binding_digest", _require_digest(self.binding_digest, "binding_digest"))
        if self.binding_digest != self.calculate_binding_digest():
            raise RuntimeCompositionError("binding_digest does not match canonical composition evidence")

    @classmethod
    def issue(
        cls,
        *,
        attestation_id: str,
        manifest: RuntimeCompositionManifest,
        occurred_at: datetime,
    ) -> RuntimeCompositionAttestation:
        occurred = _canonical_occurrence(occurred_at)
        payload = {
            "attestation_id": attestation_id,
            "manifest_digest": manifest.digest,
            "occurred_at": occurred.isoformat(),
        }
        binding_digest = hashlib.sha256(
            json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
        ).hexdigest()
        return cls(
            attestation_id=attestation_id,
            manifest=manifest,
            occurred_at=occurred,
            disposition=RuntimeCompositionDisposition.ATTESTED,
            binding_digest=binding_digest,
        )

    def calculate_binding_digest(self) -> str:
        payload = {
            "attestation_id": self.attestation_id,
            "manifest_digest": self.manifest.digest,
            "occurred_at": self.occurred_at.isoformat(),
        }
        return hashlib.sha256(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()).hexdigest()

    def to_payload(self) -> dict[str, object]:
        return {
            "attestation_id": self.attestation_id,
            "binding_digest": self.binding_digest,
            "disposition": self.disposition.value,
            "manifest": self.manifest.to_payload(),
            "occurred_at": self.occurred_at.isoformat(),
        }

    @classmethod
    def from_payload(cls, payload: object) -> RuntimeCompositionAttestation:
        required_fields = {"attestation_id", "binding_digest", "disposition", "manifest", "occurred_at"}
        if not isinstance(payload, dict) or set(payload) != required_fields:
            raise RuntimeCompositionError("runtime composition attestation has unexpected fields")
        try:
            return cls(
                attestation_id=payload["attestation_id"],
                manifest=RuntimeCompositionManifest.from_payload(payload["manifest"]),
                occurred_at=datetime.fromisoformat(payload["occurred_at"]),
                disposition=RuntimeCompositionDisposition(payload["disposition"]),
                binding_digest=payload["binding_digest"],
            )
        except (KeyError, TypeError, ValueError, RuntimeCompositionError) as error:
            raise RuntimeCompositionError("invalid runtime composition attestation") from error


@dataclass(frozen=True, slots=True, kw_only=True)
class RuntimeCompositionAdmission:
    """Immutable evidence-only result; it never contains a runtime executor, session, or permit."""

    attestation: RuntimeCompositionAttestation | None
    reason: RuntimeCompositionRejectionReason | None = None

    def __post_init__(self) -> None:
        if self.attestation is not None:
            if not isinstance(self.attestation, RuntimeCompositionAttestation):
                raise TypeError("attestation must be a RuntimeCompositionAttestation or None")
            if self.reason is not None:
                raise RuntimeCompositionError("attested composition cannot carry a rejection reason")
            return
        if not isinstance(self.reason, RuntimeCompositionRejectionReason):
            raise RuntimeCompositionError("rejected composition admission requires a typed reason")


__all__ = [
    "RuntimeComponentIdentity",
    "RuntimeCompositionAdmission",
    "RuntimeCompositionAttestation",
    "RuntimeCompositionDisposition",
    "RuntimeCompositionError",
    "RuntimeCompositionManifest",
    "RuntimeCompositionRejectionReason",
    "RuntimeDependencyBinding",
]
