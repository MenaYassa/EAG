"""Focused direct proofs for the G2.4.24 loopback visual presentation boundary."""

from __future__ import annotations

from hashlib import sha256
from io import BytesIO
from json import dumps, loads
from pathlib import Path
from typing import Any
from wsgiref.util import setup_testing_defaults

from test_support.g2_4_23_presentation_fixture import fixed_profile_presentation_fixture
from typer.testing import CliRunner

from eag.cli import app
from eag.governed_visual_presentation import create_fixed_profile_visual_application


def _payload_for_fixture(fixture: object, *, profile: str | None = None) -> dict[str, object]:
    submission = fixture.submission
    custody = submission.custody_request
    return {
        "submission_id": submission.submission_id,
        "profile": submission.selected_profile_token if profile is None else profile,
        "requested_at": submission.requested_at.isoformat(),
        "expires_at": submission.expires_at.isoformat(),
        "attestation_id": custody.attestation_id,
        "execution_id": custody.execution_id,
        "run_id": custody.run_id,
        "workspace_id": custody.workspace_id,
        "workspace_root": str(custody.workspace_root),
        "source_repository_root": str(custody.source_repository_root),
        "audit_root": str(custody.audit_root),
        "control_root": str(custody.control_root),
        "composition_attestation": submission.runtime_composition_attestation.to_payload(),
    }


def _wsgi_request(
    *,
    method: str,
    path: str,
    payload: dict[str, object] | None = None,
    remote_address: str = "127.0.0.1",
    content_type: str | None = "application/json",
) -> tuple[str, dict[str, str], bytes]:
    application = create_fixed_profile_visual_application()
    body = b"" if payload is None else dumps(payload).encode("utf-8")
    environ: dict[str, Any] = {}
    setup_testing_defaults(environ)
    environ.update(
        {
            "REQUEST_METHOD": method,
            "PATH_INFO": path,
            "REMOTE_ADDR": remote_address,
            "CONTENT_LENGTH": str(len(body)),
            "wsgi.input": BytesIO(body),
        }
    )
    if content_type is not None:
        environ["CONTENT_TYPE"] = content_type
    response: dict[str, object] = {}

    def start_response(status: str, headers: list[tuple[str, str]]) -> None:
        response["status"] = status
        response["headers"] = dict(headers)

    response_body = b"".join(application(environ, start_response))
    return response["status"], response["headers"], response_body  # type: ignore[return-value]


def test_visual_page_and_cli_are_local_static_presentation_only() -> None:
    status, headers, body = _wsgi_request(method="GET", path="/")

    assert status == "200 OK"
    assert headers["Content-Type"] == "text/html; charset=utf-8"
    assert b"EAG \xe2\x80\x94 Build an App" in body
    assert b"modern_todo_static_v1" in body
    assert b"/app.js" in body
    assert b"http://" not in body
    assert b"https://" not in body

    result = CliRunner().invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "serve-fixed-profile-visual" in result.output


def test_visual_relays_exact_token_to_real_issuer_and_returns_receipt_facts(tmp_path: Path) -> None:
    fixture = fixed_profile_presentation_fixture(tmp_path, identity="g2424-focused-success")
    status, _, body = _wsgi_request(method="POST", path="/api/construct", payload=_payload_for_fixture(fixture))
    response = loads(body)

    assert status == "200 OK"
    assert response["selected_profile"] == "modern_todo_static_v1"
    assert response["presentation_disposition"] == "receipt_available"
    assert response["construction_disposition"] == "construction_files_created"
    assert response["receipt_files"]
    assert {item["relative_path"] for item in response["receipt_files"]} == {
        "README.md",
        "app.js",
        "index.html",
        "styles.css",
    }
    assert "workspace_root" not in response
    assert "handle" not in response
    assert "descriptor" not in response
    assert "custody" not in response

    for item in response["receipt_files"]:
        actual = (fixture.workspace_root / item["relative_path"]).read_bytes()
        assert len(actual) == item["byte_count"]
        assert sha256(actual).hexdigest() == item["content_digest"]


def test_visual_unsupported_token_is_refused_by_g2_4_21_before_handoff_or_effect(tmp_path: Path) -> None:
    fixture = fixed_profile_presentation_fixture(tmp_path, identity="g2424-focused-refusal")
    before = tuple(sorted(path.name for path in fixture.workspace_root.iterdir()))
    status, _, body = _wsgi_request(
        method="POST",
        path="/api/construct",
        payload=_payload_for_fixture(fixture, profile="unsupported_visual_profile"),
    )
    response = loads(body)

    assert status == "200 OK"
    assert response["selected_profile"] == "unsupported_visual_profile"
    assert response["presentation_disposition"] == "upstream_refused"
    assert response["failure_stage"] == "g2_4_21_profile_issuance"
    assert response["receipt_files"] == []
    assert tuple(sorted(path.name for path in fixture.workspace_root.iterdir())) == before


def test_visual_content_type_refusal_precedes_submission_and_preserves_workspace(tmp_path: Path) -> None:
    fixture = fixed_profile_presentation_fixture(tmp_path, identity="g2424-focused-content-type")
    payload = _payload_for_fixture(fixture)
    before = tuple(sorted(path.name for path in fixture.workspace_root.iterdir()))

    for content_type in (None, "text/plain", "application/json; charset=utf-8"):
        status, _, body = _wsgi_request(
            method="POST",
            path="/api/construct",
            payload=payload,
            content_type=content_type,
        )
        assert status == "415 Unsupported Media Type"
        assert loads(body) == {"error": "unsupported media type"}
        assert tuple(sorted(path.name for path in fixture.workspace_root.iterdir())) == before

    status, _, body = _wsgi_request(
        method="POST",
        path="/api/construct",
        payload=payload,
        content_type="application/json",
    )
    assert status == "200 OK"
    assert loads(body)["presentation_disposition"] == "receipt_available"


def test_visual_application_refuses_non_loopback_requests() -> None:
    status, _, body = _wsgi_request(method="GET", path="/", remote_address="203.0.113.9")

    assert status == "403 Forbidden"
    assert loads(body) == {"error": "loopback only"}
