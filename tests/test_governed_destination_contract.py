"""Focused deterministic tests for frozen G2.4.18 destination contract evidence."""

from __future__ import annotations

from dataclasses import fields
from datetime import timedelta, timezone

import pytest
from test_support.g2_4_18_destination_contract_fixture import (
    EffectSentinel,
    assess_without_progression,
    assessment_request,
    contract_variant,
    destination_contract_fixture,
)

from eag.governed_destination_contract import (
    DestinationContractAssessmentRequest,
    DestinationContractAssessor,
    DestinationContractDisposition,
    DestinationContractEvidenceError,
    DestinationContractFindingCode,
    ExternalDestinationContractEvidence,
)


def _request_kwargs(fixture: object) -> dict[str, object]:
    return {
        "assessment_request_id": "g2418-strict-request",
        "promotion_request": fixture.promotion_request,
        "promotion_assessment": fixture.promotion_assessment,
        "transition_intent": fixture.transition_intent,
        "authorization": fixture.authorization,
        "authorization_assessment": fixture.authorization_assessment,
        "contract": fixture.contract,
        "timestamp": fixture.timestamp,
    }


def test_valid_request_is_frozen_canonical_and_self_validating() -> None:
    fixture = destination_contract_fixture(identity="focused-valid")
    first = DestinationContractAssessmentRequest(**_request_kwargs(fixture))
    second = DestinationContractAssessmentRequest(**_request_kwargs(fixture))

    assert first.to_payload() == second.to_payload()
    assert first.request_digest == second.request_digest
    assert first.calculate_digest() == first.request_digest
    with pytest.raises((AttributeError, TypeError)):
        first.contract = fixture.contract  # type: ignore[misc]
    assert all(not isinstance(getattr(first, field.name), (dict, list, set)) for field in fields(first))


def test_request_normalizes_equivalent_timestamps_deterministically() -> None:
    fixture = destination_contract_fixture(identity="focused-time")
    utc_request = assessment_request(fixture, assessment_request_id="g2418-time")
    offset_time = fixture.timestamp.astimezone(timezone(timedelta(hours=3)))
    offset_request = assessment_request(
        fixture, assessment_request_id="g2418-time", timestamp=offset_time
    )

    assert offset_request.timestamp == utc_request.timestamp
    assert offset_request.to_payload() == utc_request.to_payload()
    assert offset_request.request_digest == utc_request.request_digest


@pytest.mark.parametrize(
    ("field_name", "value", "error_type"),
    (
        ("promotion_request", object(), TypeError),
        ("promotion_assessment", object(), TypeError),
        ("transition_intent", object(), TypeError),
        ("authorization", object(), TypeError),
        ("authorization_assessment", object(), TypeError),
        ("contract", {"mutable": "dictionary"}, TypeError),
        ("timestamp", "not-a-timestamp", DestinationContractEvidenceError),
        ("schema_version", "unsupported-v9", DestinationContractEvidenceError),
        ("request_digest", "not-a-sha256", DestinationContractEvidenceError),
    ),
)
def test_request_rejects_invalid_evidence_at_construction(
    field_name: str, value: object, error_type: type[Exception]
) -> None:
    fixture = destination_contract_fixture(identity="focused-strict")
    kwargs = _request_kwargs(fixture)
    kwargs[field_name] = value

    with pytest.raises(error_type):
        DestinationContractAssessmentRequest(**kwargs)  # type: ignore[arg-type]


def test_assessor_preserves_valid_and_binding_refusal_behavior(tmp_path: object) -> None:
    fixture = destination_contract_fixture(identity="focused-assessor")
    effects = EffectSentinel()
    assessor = DestinationContractAssessor()
    valid = assess_without_progression(
        assessor=assessor, request=assessment_request(fixture), effects=effects, temporary_root=tmp_path
    )
    altered = assess_without_progression(
        assessor=assessor,
        request=assessment_request(
            fixture,
            contract=contract_variant(fixture.contract, destination_identity="internal-registry"),
        ),
        effects=effects,
        temporary_root=tmp_path,
    )

    assert valid.disposition is DestinationContractDisposition.CONTRACT_ATTESTED
    assert altered.disposition is DestinationContractDisposition.NOT_ATTESTED
    assert DestinationContractFindingCode.CONTRACT_DESTINATION_MISMATCH in {
        finding.code for finding in altered.findings
    }
    effects.assert_zero()


def test_contract_raw_payload_rejection_stays_outside_request_boundary() -> None:
    fixture = destination_contract_fixture(identity="focused-raw")
    raw_payload = fixture.contract.to_payload()
    raw_payload["contract_digest"] = "0" * 64

    with pytest.raises(DestinationContractEvidenceError):
        ExternalDestinationContractEvidence.from_payload(raw_payload)
    with pytest.raises(TypeError):
        DestinationContractAssessmentRequest(**{**_request_kwargs(fixture), "contract": raw_payload})  # type: ignore[arg-type]
