"""Loopback-only G2.4.24 WSGI presentation over public G2.4.23 contracts."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import asdict, dataclass
from datetime import datetime
from importlib.resources import files
from json import JSONDecodeError, dumps, loads
from pathlib import Path
from typing import Any
from wsgiref.simple_server import make_server

from eag.governed_composition import RuntimeCompositionAttestation, RuntimeCompositionError
from eag.governed_presentation import (
    FixedProfilePresentationSubmission,
    FixedProfileTerminalView,
    submit_fixed_profile_construction,
)
from eag.governed_workspace import (
    FileDurableWorkspaceCustodyStore,
    WorkspaceCustodyGate,
    WorkspaceCustodyRequest,
)

_LOOPBACK_ADDRESSES = frozenset({"127.0.0.1", "::1"})
_MAX_REQUEST_BYTES = 64 * 1024
_STATIC_ASSETS = {
    "/": ("static/index.html", "text/html; charset=utf-8"),
    "/app.css": ("static/app.css", "text/css; charset=utf-8"),
    "/app.js": ("static/app.js", "application/javascript; charset=utf-8"),
}


@dataclass(frozen=True, slots=True, kw_only=True)
class VisualReceiptFile:
    """Immutable receipt fact that is already present in G2.4.23 output."""

    relative_path: str
    byte_count: int
    content_digest: str


@dataclass(frozen=True, slots=True, kw_only=True)
class FixedProfileVisualView:
    """Restricted visual projection; it contains no operational or custody authority."""

    presentation_disposition: str
    selected_profile: str
    profile_version: str | None
    source_specification_digest: str | None
    intent_request_id: str | None
    intent_request_digest: str | None
    intent_assessment_id: str | None
    intent_assessment_digest: str | None
    work_order_id: str | None
    work_order_digest: str | None
    work_order_assessment_id: str | None
    work_order_assessment_digest: str | None
    work_order_expires_at: str | None
    authorization_id: str | None
    authorization_digest: str | None
    plan_digest: str | None
    construction_disposition: str | None
    construction_failure: str | None
    failure_stage: str | None
    failure_code: str | None
    receipt_files: tuple[VisualReceiptFile, ...]

    def as_payload(self) -> dict[str, Any]:
        """Return only JSON-compatible values already represented by this projection."""
        payload = asdict(self)
        payload["receipt_files"] = [asdict(item) for item in self.receipt_files]
        return payload


def project_terminal_view(*, view: FixedProfileTerminalView) -> FixedProfileVisualView:
    """Project the published immutable terminal view without inspecting a workspace."""
    if not isinstance(view, FixedProfileTerminalView):
        raise TypeError("view must be FixedProfileTerminalView")
    return FixedProfileVisualView(
        presentation_disposition=view.disposition.value,
        selected_profile=view.selected_profile,
        profile_version=view.profile_version,
        source_specification_digest=view.source_specification_digest,
        intent_request_id=view.intent_request_id,
        intent_request_digest=view.intent_request_digest,
        intent_assessment_id=view.intent_assessment_id,
        intent_assessment_digest=view.intent_assessment_digest,
        work_order_id=view.work_order_id,
        work_order_digest=view.work_order_digest,
        work_order_assessment_id=view.work_order_assessment_id,
        work_order_assessment_digest=view.work_order_assessment_digest,
        work_order_expires_at=None
        if view.work_order_expires_at is None
        else view.work_order_expires_at.isoformat(),
        authorization_id=view.authorization_id,
        authorization_digest=view.authorization_digest,
        plan_digest=view.plan_digest,
        construction_disposition=None
        if view.construction_disposition is None
        else view.construction_disposition.value,
        construction_failure=view.construction_failure,
        failure_stage=None if view.failure_stage is None else view.failure_stage.value,
        failure_code=view.failure_code,
        receipt_files=tuple(
            VisualReceiptFile(
                relative_path=item.relative_path,
                byte_count=item.byte_count,
                content_digest=item.content_digest,
            )
            for item in view.receipt_files
        ),
    )


def submission_from_visual_payload(*, payload: Mapping[str, object]) -> FixedProfilePresentationSubmission:
    """Decode caller-supplied public G2.4.23 submission values without profile judgment."""
    try:
        profile = _required_text(payload, "profile")
        composition_payload = payload["composition_attestation"]
        if not isinstance(composition_payload, dict):
            raise TypeError("composition_attestation must be an object")
        control_root = Path(_required_text(payload, "control_root"))
        return FixedProfilePresentationSubmission(
            submission_id=_required_text(payload, "submission_id"),
            selected_profile_token=profile,
            requested_at=_required_datetime(payload, "requested_at"),
            expires_at=_required_datetime(payload, "expires_at"),
            custody_gate=WorkspaceCustodyGate(
                custody_store=FileDurableWorkspaceCustodyStore(control_root=control_root)
            ),
            custody_request=WorkspaceCustodyRequest(
                attestation_id=_required_text(payload, "attestation_id"),
                execution_id=_required_text(payload, "execution_id"),
                run_id=_required_text(payload, "run_id"),
                workspace_id=_required_text(payload, "workspace_id"),
                workspace_root=Path(_required_text(payload, "workspace_root")),
                source_repository_root=Path(_required_text(payload, "source_repository_root")),
                audit_root=Path(_required_text(payload, "audit_root")),
                control_root=control_root,
            ),
            runtime_composition_attestation=RuntimeCompositionAttestation.from_payload(composition_payload),
        )
    except (KeyError, TypeError, ValueError, RuntimeCompositionError) as error:
        raise ValueError(str(error)) from error


class FixedProfileVisualApplication:
    """Small loopback-only WSGI application that consumes one public G2.4.23 flow."""

    def __call__(
        self,
        environ: Mapping[str, object],
        start_response: Callable[[str, list[tuple[str, str]]], object],
    ) -> Iterable[bytes]:
        remote_address = environ.get("REMOTE_ADDR")
        if remote_address not in _LOOPBACK_ADDRESSES:
            return self._json_response(start_response, "403 Forbidden", {"error": "loopback only"})

        method = environ.get("REQUEST_METHOD")
        path = environ.get("PATH_INFO")
        if method == "GET" and isinstance(path, str) and path in _STATIC_ASSETS:
            asset_name, content_type = _STATIC_ASSETS[path]
            return self._asset_response(start_response, asset_name, content_type)
        if method == "POST" and path == "/api/construct":
            return self._construct_response(environ, start_response)
        return self._json_response(start_response, "404 Not Found", {"error": "not found"})

    def _construct_response(
        self,
        environ: Mapping[str, object],
        start_response: Callable[[str, list[tuple[str, str]]], object],
    ) -> Iterable[bytes]:
        if environ.get("CONTENT_TYPE") != "application/json":
            return self._json_response(
                start_response,
                "415 Unsupported Media Type",
                {"error": "unsupported media type"},
            )
        try:
            payload = _json_request_payload(environ)
            submission = submission_from_visual_payload(payload=payload)
            visual_view = project_terminal_view(
                view=submit_fixed_profile_construction(submission=submission)
            )
        except ValueError as error:
            return self._json_response(start_response, "400 Bad Request", {"error": str(error)})
        return self._json_response(start_response, "200 OK", visual_view.as_payload())

    @staticmethod
    def _asset_response(
        start_response: Callable[[str, list[tuple[str, str]]], object],
        asset_name: str,
        content_type: str,
    ) -> Iterable[bytes]:
        content = files("eag.governed_visual_presentation").joinpath(asset_name).read_bytes()
        start_response(
            "200 OK",
            [
                ("Content-Type", content_type),
                ("Content-Length", str(len(content))),
                ("Cache-Control", "no-store"),
            ],
        )
        return [content]

    @staticmethod
    def _json_response(
        start_response: Callable[[str, list[tuple[str, str]]], object],
        status: str,
        payload: Mapping[str, object],
    ) -> Iterable[bytes]:
        content = dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        start_response(
            status,
            [
                ("Content-Type", "application/json; charset=utf-8"),
                ("Content-Length", str(len(content))),
                ("Cache-Control", "no-store"),
            ],
        )
        return [content]


def create_fixed_profile_visual_application() -> FixedProfileVisualApplication:
    """Create the public visual presentation adapter with no configurable network target."""
    return FixedProfileVisualApplication()


def start_fixed_profile_visual_host(*, port: int) -> None:
    """Serve only on loopback until the local caller terminates the process."""
    if not isinstance(port, int) or not 1 <= port <= 65535:
        raise ValueError("port must be an integer between 1 and 65535")
    application = create_fixed_profile_visual_application()
    with make_server("127.0.0.1", port, application) as server:
        server.serve_forever()


def _json_request_payload(environ: Mapping[str, object]) -> Mapping[str, object]:
    content_length = environ.get("CONTENT_LENGTH", "")
    if not isinstance(content_length, str) or not content_length.isdecimal():
        raise ValueError("content length must be a non-negative decimal value")
    request_length = int(content_length)
    if request_length > _MAX_REQUEST_BYTES:
        raise ValueError("request payload exceeds the local visual boundary")
    stream = environ.get("wsgi.input")
    if not hasattr(stream, "read"):
        raise ValueError("missing request body")
    raw_payload = stream.read(request_length)
    if not isinstance(raw_payload, bytes):
        raise ValueError("request body must be bytes")
    try:
        payload = loads(raw_payload.decode("utf-8"))
    except (UnicodeDecodeError, JSONDecodeError) as error:
        raise ValueError("request payload must be valid UTF-8 JSON") from error
    if not isinstance(payload, dict):
        raise ValueError("request payload must be a JSON object")
    return payload


def _required_text(payload: Mapping[str, object], field: str) -> str:
    value = payload[field]
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be a non-empty string")
    return value


def _required_datetime(payload: Mapping[str, object], field: str) -> datetime:
    return datetime.fromisoformat(_required_text(payload, field))


__all__ = [
    "FixedProfileVisualApplication",
    "FixedProfileVisualView",
    "VisualReceiptFile",
    "create_fixed_profile_visual_application",
    "project_terminal_view",
    "start_fixed_profile_visual_host",
    "submission_from_visual_payload",
]
