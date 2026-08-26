"""EBS-040 — loopback visual presentation over the published fixed-profile chain."""

from __future__ import annotations

from hashlib import sha256
from importlib.resources import files
from io import BytesIO
from json import dumps, loads
from pathlib import Path
from typing import Any
from wsgiref.util import setup_testing_defaults

from test_support.g2_4_23_presentation_fixture import fixed_profile_presentation_fixture

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


def _request(
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
    captured: dict[str, object] = {}

    def start_response(status: str, headers: list[tuple[str, str]]) -> None:
        captured["status"] = status
        captured["headers"] = dict(headers)

    response_body = b"".join(application(environ, start_response))
    return captured["status"], captured["headers"], response_body  # type: ignore[return-value]


def test_ebs_040_exact_token_reaches_real_chain_and_visual_receipts_are_truthful(tmp_path: Path) -> None:
    fixture = fixed_profile_presentation_fixture(tmp_path, identity="ebs-040-success")
    retained_root = fixture.workspace_root

    status, _, body = _request(method="POST", path="/api/construct", payload=_payload_for_fixture(fixture))
    response = loads(body)

    assert status == "200 OK"
    assert response["selected_profile"] == "modern_todo_static_v1"
    assert response["presentation_disposition"] == "receipt_available"
    assert response["construction_disposition"] == "construction_files_created"
    receipt_paths = tuple(item["relative_path"] for item in response["receipt_files"])
    retained_paths = tuple(
        sorted(path.relative_to(retained_root).as_posix() for path in retained_root.rglob("*") if path.is_file())
    )
    assert set(receipt_paths) == set(retained_paths)

    for item in response["receipt_files"]:
        actual_content = (retained_root / item["relative_path"]).read_bytes()
        assert len(actual_content) == item["byte_count"]
        assert sha256(actual_content).hexdigest() == item["content_digest"]

    forbidden_visual_keys = {
        "workspace_root",
        "source_repository_root",
        "audit_root",
        "control_root",
        "handle",
        "descriptor",
        "custody",
        "provenance_registry",
    }
    assert forbidden_visual_keys.isdisjoint(response)


def test_ebs_040_unsupported_token_is_refused_by_g2_4_21_before_handoff_or_effect(tmp_path: Path) -> None:
    fixture = fixed_profile_presentation_fixture(tmp_path, identity="ebs-040-refusal")
    before = tuple(sorted(path.name for path in fixture.workspace_root.iterdir()))

    status, _, body = _request(
        method="POST",
        path="/api/construct",
        payload=_payload_for_fixture(fixture, profile="not_a_fixed_profile"),
    )
    response = loads(body)

    assert status == "200 OK"
    assert response["selected_profile"] == "not_a_fixed_profile"
    assert response["presentation_disposition"] == "upstream_refused"
    assert response["failure_stage"] == "g2_4_21_profile_issuance"
    assert response["receipt_files"] == []
    assert tuple(sorted(path.name for path in fixture.workspace_root.iterdir())) == before


def test_ebs_040_content_type_refusals_preserve_workspace_and_exact_json_control_constructs(
    tmp_path: Path,
) -> None:
    fixture = fixed_profile_presentation_fixture(tmp_path, identity="ebs-040-content-type")
    payload = _payload_for_fixture(fixture)
    before = tuple(sorted(path.name for path in fixture.workspace_root.iterdir()))

    for content_type in (None, "text/plain", "application/json; charset=utf-8"):
        status, _, body = _request(
            method="POST",
            path="/api/construct",
            payload=payload,
            content_type=content_type,
        )
        assert status == "415 Unsupported Media Type"
        assert loads(body) == {"error": "unsupported media type"}
        assert tuple(sorted(path.name for path in fixture.workspace_root.iterdir())) == before

    status, _, body = _request(
        method="POST",
        path="/api/construct",
        payload=payload,
        content_type="application/json",
    )
    response = loads(body)
    assert status == "200 OK"
    assert response["presentation_disposition"] == "receipt_available"
    assert response["receipt_files"]


def test_ebs_040_loopback_static_and_negative_capability_boundary() -> None:
    status, headers, page = _request(method="GET", path="/")
    remote_status, _, remote_body = _request(method="GET", path="/", remote_address="198.51.100.7")
    static_client = files("eag.governed_visual_presentation").joinpath("static/app.js").read_text()

    assert status == "200 OK"
    assert headers["Content-Type"] == "text/html; charset=utf-8"
    assert b"modern_todo_static_v1" in page
    assert b"https://" not in page
    assert b"http://" not in page
    assert remote_status == "403 Forbidden"
    assert loads(remote_body) == {"error": "loopback only"}
    for prohibited_capability in ("subprocess", "webbrowser", "eval(", "exec(", "WebSocket", "http://", "https://"):
        assert prohibited_capability not in static_client
