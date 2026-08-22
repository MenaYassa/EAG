"""Deterministic tests for the additive G2.4.4 pre-mutation authority boundary."""

from __future__ import annotations

from dataclasses import replace

import pytest

from eag.governed_execution import (
    FreshIterationAuthority,
    FreshIterationAuthorityError,
    validate_fresh_authority,
)


def _authority(*, iteration: int, suffix: str) -> FreshIterationAuthority:
    return FreshIterationAuthority(
        execution_id="execution-1",
        iteration=iteration,
        context_artifact_id=f"context-artifact-{suffix}",
        context_fingerprint=f"context-fingerprint-{suffix}",
        decision_request_id=f"decision-request-{suffix}",
        decision_id=f"decision-{suffix}",
        proposal_id=f"proposal-{suffix}",
        authorization_id=f"authorization-{suffix}",
    )


def test_fresh_iteration_authority_accepts_valid_next_iteration() -> None:
    previous = _authority(iteration=1, suffix="one")
    candidate = _authority(iteration=2, suffix="two")

    validate_fresh_authority(previous, candidate)


@pytest.mark.parametrize(
    "field_name",
    (
        "context_artifact_id",
        "context_fingerprint",
        "decision_request_id",
        "decision_id",
        "proposal_id",
        "authorization_id",
    ),
)
def test_fresh_iteration_authority_rejects_reused_executable_identity(field_name: str) -> None:
    previous = _authority(iteration=1, suffix="one")
    candidate = _authority(iteration=2, suffix="two")
    candidate = replace(candidate, **{field_name: getattr(previous, field_name)})

    with pytest.raises(FreshIterationAuthorityError, match="stale"):
        validate_fresh_authority(previous, candidate)


def test_fresh_iteration_authority_rejects_other_execution() -> None:
    previous = _authority(iteration=1, suffix="one")
    candidate = replace(_authority(iteration=2, suffix="two"), execution_id="execution-other")

    with pytest.raises(FreshIterationAuthorityError, match="another execution"):
        validate_fresh_authority(previous, candidate)


@pytest.mark.parametrize("iteration", (1, 3))
def test_fresh_iteration_authority_rejects_nonsequential_iteration(iteration: int) -> None:
    previous = _authority(iteration=1, suffix="one")
    candidate = _authority(iteration=iteration, suffix="two")

    with pytest.raises(FreshIterationAuthorityError, match="next serial iteration"):
        validate_fresh_authority(previous, candidate)


@pytest.mark.parametrize("field_name", ("receipt_id", "verification_id"))
def test_fresh_iteration_authority_explicitly_excludes_post_mutation_identity_fields(
    field_name: str,
) -> None:
    assert field_name not in FreshIterationAuthority.__dataclass_fields__


@pytest.mark.parametrize("field_name", ("execution_id", "context_artifact_id", "authorization_id"))
def test_fresh_iteration_authority_rejects_empty_required_fields(field_name: str) -> None:
    values = {
        "execution_id": "execution-1",
        "iteration": 1,
        "context_artifact_id": "context-artifact-1",
        "context_fingerprint": "context-fingerprint-1",
        "decision_request_id": "request-1",
        "decision_id": "decision-1",
        "proposal_id": "proposal-1",
        "authorization_id": "authorization-1",
    }
    values[field_name] = ""

    with pytest.raises(FreshIterationAuthorityError, match="cannot be empty"):
        FreshIterationAuthority(**values)
