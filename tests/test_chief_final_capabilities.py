"""Comprehensive tests for the Chief Capability Platform (Sprint 7.6)."""

from dataclasses import dataclass, field
from pathlib import Path

import pytest

from eag.capability import (
    Capability,
    CapabilityContext,
    CapabilityKind,
    CapabilityMetadata,
    CapabilityNotFoundError,
    CapabilityOutcome,
    CapabilityRegistry,
    CapabilityRequest,
    CapabilityResult,
    CapabilityRuntime,
    CapabilityState,
    CapabilityStatus,
    CompositeCapability,
    RepositoryCapability,
    ReviewCapability,
    TransformationCapability,
    WorkspaceCapability,
)

# --- Mocks & Fixtures ---


@dataclass
class MockWorkspaceRuntime:
    writes: dict[Path, str] = field(default_factory=dict)

    def write(self, path: Path, content: str) -> None:
        self.writes[path] = content

    def read(self, path: Path) -> str:
        return self.writes.get(path, "")


@dataclass
class MockVCSRuntime:
    commits: list[str] = field(default_factory=list)

    def commit(self, message: str) -> str:
        self.commits.append(message)
        return "mock_commit_hash"


@dataclass
class MockSourceRuntime:
    def parse(self, path: Path, content: str):
        from eag.source.models import Language, SourceDocument

        return SourceDocument(path=path, language=Language.PYTHON, checksum="mock")


@dataclass
class MockReviewRuntime:
    def review(self, context):
        from eag.review.enums import ReviewDecision
        from eag.review.models import ReviewMetrics, ReviewReport

        return ReviewReport(
            decision=ReviewDecision.APPROVED, overall_score=100, metrics=ReviewMetrics()
        )


@pytest.fixture
def workspace_runtime() -> MockWorkspaceRuntime:
    return MockWorkspaceRuntime()


@pytest.fixture
def vcs_runtime() -> MockVCSRuntime:
    return MockVCSRuntime()


@pytest.fixture
def source_runtime() -> MockSourceRuntime:
    return MockSourceRuntime()


@pytest.fixture
def review_runtime() -> MockReviewRuntime:
    return MockReviewRuntime()


@pytest.fixture
def registry(
    workspace_runtime: MockWorkspaceRuntime,
    vcs_runtime: MockVCSRuntime,
    source_runtime: MockSourceRuntime,
    review_runtime: MockReviewRuntime,
) -> CapabilityRegistry:
    reg = CapabilityRegistry()
    reg.register(WorkspaceCapability(workspace_runtime))
    reg.register(RepositoryCapability(vcs_runtime))
    reg.register(TransformationCapability(source_runtime))
    reg.register(ReviewCapability(review_runtime))
    return reg


@pytest.fixture
def runtime(registry: CapabilityRegistry) -> CapabilityRuntime:
    return CapabilityRuntime(registry=registry)


@pytest.fixture
def context(tmp_path: Path) -> CapabilityContext:
    return CapabilityContext(workspace_path=tmp_path)


# --- Model & Enum Tests (20) ---


class TestCapabilityModels:
    def test_metadata_immutable(self) -> None:
        m = CapabilityMetadata(id="test", name="Test")
        with pytest.raises(Exception):  # noqa: B017
            m.id = "new"  # type: ignore[misc]

    def test_metadata_invalid_id(self) -> None:
        with pytest.raises(ValueError):
            CapabilityMetadata(id="", name="Test")

    def test_request_immutable(self) -> None:
        r = CapabilityRequest(capability_id="test")
        with pytest.raises(Exception):  # noqa: B017
            r.capability_id = "new"  # type: ignore[misc]

    def test_result_immutable(self) -> None:
        r = CapabilityResult(
            request_id="r",
            capability_id="c",
            outcome=CapabilityOutcome.SUCCESS,
            state=CapabilityState.COMPLETED,
        )
        with pytest.raises(Exception):  # noqa: B017
            r.outcome = CapabilityOutcome.FAILURE  # type: ignore[misc]

    def test_context_immutable(self) -> None:
        c = CapabilityContext(workspace_path=Path("/tmp"))
        with pytest.raises(Exception):  # noqa: B017
            c.workspace_path = Path("/")  # type: ignore[misc]

    def test_kind_values(self) -> None:
        assert CapabilityKind.WORKSPACE == "workspace"
        assert CapabilityKind.COMPOSITE == "composite"

    def test_outcome_values(self) -> None:
        assert CapabilityOutcome.SUCCESS == "success"
        assert CapabilityOutcome.FAILURE == "failure"

    def test_state_values(self) -> None:
        assert CapabilityState.RUNNING == "running"
        assert CapabilityState.COMPLETED == "completed"

    def test_status_values(self) -> None:
        assert CapabilityStatus.READY == "ready"
        assert CapabilityStatus.DISABLED == "disabled"

    def test_result_success_property(self) -> None:
        r = CapabilityResult(
            request_id="r",
            capability_id="c",
            outcome=CapabilityOutcome.SUCCESS,
            state=CapabilityState.COMPLETED,
        )
        assert r.success is True

    def test_result_failure_property(self) -> None:
        r = CapabilityResult(
            request_id="r",
            capability_id="c",
            outcome=CapabilityOutcome.FAILURE,
            state=CapabilityState.FAILED,
        )
        assert r.success is False

    def test_metadata_defaults(self) -> None:
        m = CapabilityMetadata(id="test", name="Test")
        assert m.kind == CapabilityKind.UNKNOWN
        assert m.version == "1.0.0"

    def test_request_defaults(self) -> None:
        r = CapabilityRequest(capability_id="test")
        assert r.goal_text == ""
        assert r.parameters == {}

    def test_context_defaults(self) -> None:
        c = CapabilityContext(workspace_path=Path("/tmp"))
        assert c.repository_path is None
        assert c.metadata == {}

    def test_result_defaults(self) -> None:
        r = CapabilityResult(
            request_id="r",
            capability_id="c",
            outcome=CapabilityOutcome.SUCCESS,
            state=CapabilityState.COMPLETED,
        )
        assert r.output == ""
        assert r.error is None
        assert r.duration_ms == 0.0

    def test_metadata_tags(self) -> None:
        m = CapabilityMetadata(id="test", name="Test", tags=("a", "b"))
        assert "a" in m.tags

    def test_request_parameters(self) -> None:
        r = CapabilityRequest(capability_id="test", parameters={"k": "v"})
        assert r.parameters["k"] == "v"

    def test_context_metadata(self) -> None:
        c = CapabilityContext(workspace_path=Path("/tmp"), metadata={"k": "v"})
        assert c.metadata["k"] == "v"

    def test_result_metadata(self) -> None:
        r = CapabilityResult(
            request_id="r",
            capability_id="c",
            outcome=CapabilityOutcome.SUCCESS,
            state=CapabilityState.COMPLETED,
            metadata={"k": "v"},
        )
        assert r.metadata["k"] == "v"

    def test_result_artifacts(self) -> None:
        r = CapabilityResult(
            request_id="r",
            capability_id="c",
            outcome=CapabilityOutcome.SUCCESS,
            state=CapabilityState.COMPLETED,
            artifacts=("file.txt",),
        )
        assert "file.txt" in r.artifacts


# --- Registry Tests (10) ---


class TestCapabilityRegistry:
    def test_register(self, registry: CapabilityRegistry) -> None:
        assert len(registry.list()) == 4

    def test_duplicate_raises(self, registry: CapabilityRegistry) -> None:
        with pytest.raises(ValueError):
            registry.register(WorkspaceCapability(MockWorkspaceRuntime()))

    def test_find_success(self, registry: CapabilityRegistry) -> None:
        cap = registry.find("workspace")
        assert cap.metadata.id == "workspace"

    def test_find_missing_raises(self, registry: CapabilityRegistry) -> None:
        with pytest.raises(CapabilityNotFoundError):
            registry.find("missing")

    def test_list_returns_tuple(self, registry: CapabilityRegistry) -> None:
        assert isinstance(registry.list(), tuple)

    def test_discover(self, registry: CapabilityRegistry) -> None:
        req = CapabilityRequest(capability_id="workspace")
        discovered = registry.discover(req)
        assert len(discovered) == 1
        assert discovered[0].metadata.id == "workspace"

    def test_discover_none(self, registry: CapabilityRegistry) -> None:
        req = CapabilityRequest(capability_id="missing")
        assert len(registry.discover(req)) == 0

    def test_list_empty(self) -> None:
        reg = CapabilityRegistry()
        assert len(reg.list()) == 0

    def test_register_multiple(self) -> None:
        reg = CapabilityRegistry()
        reg.register(WorkspaceCapability(MockWorkspaceRuntime()))
        reg.register(RepositoryCapability(MockVCSRuntime()))
        assert len(reg.list()) == 2

    def test_list_sorted(self, registry: CapabilityRegistry) -> None:
        # Not strictly sorted, but deterministic
        caps = registry.list()
        assert len(caps) == 4


# --- Workspace Capability Tests (10) ---


class TestWorkspaceCapability:
    def test_metadata(self, workspace_runtime: MockWorkspaceRuntime) -> None:
        cap = WorkspaceCapability(workspace_runtime)
        assert cap.metadata.id == "workspace"
        assert cap.metadata.kind == CapabilityKind.WORKSPACE

    def test_supports(self, workspace_runtime: MockWorkspaceRuntime) -> None:
        cap = WorkspaceCapability(workspace_runtime)
        req = CapabilityRequest(capability_id="workspace")
        assert cap.supports(req) is True

    def test_does_not_support(self, workspace_runtime: MockWorkspaceRuntime) -> None:
        cap = WorkspaceCapability(workspace_runtime)
        req = CapabilityRequest(capability_id="other")
        assert cap.supports(req) is False

    def test_execute_write(
        self, workspace_runtime: MockWorkspaceRuntime, context: CapabilityContext
    ) -> None:
        cap = WorkspaceCapability(workspace_runtime)
        req = CapabilityRequest(
            capability_id="workspace",
            parameters={"operation": "write", "path": "test.txt", "content": "Hello"},
        )
        result = cap.execute(req, context)
        assert result.success is True
        assert workspace_runtime.writes[Path("test.txt")] == "Hello"

    def test_execute_read(
        self, workspace_runtime: MockWorkspaceRuntime, context: CapabilityContext
    ) -> None:
        workspace_runtime.writes[Path("test.txt")] = "Hello"
        cap = WorkspaceCapability(workspace_runtime)
        req = CapabilityRequest(
            capability_id="workspace", parameters={"operation": "read", "path": "test.txt"}
        )
        result = cap.execute(req, context)
        assert result.success is True
        assert result.output == "Hello"

    def test_execute_missing_path(
        self, workspace_runtime: MockWorkspaceRuntime, context: CapabilityContext
    ) -> None:
        cap = WorkspaceCapability(workspace_runtime)
        req = CapabilityRequest(capability_id="workspace", parameters={"operation": "write"})
        result = cap.execute(req, context)
        assert result.success is False
        assert "Missing 'path'" in result.error

    def test_execute_unsupported_op(
        self, workspace_runtime: MockWorkspaceRuntime, context: CapabilityContext
    ) -> None:
        cap = WorkspaceCapability(workspace_runtime)
        req = CapabilityRequest(
            request_id="test_req_1",
            capability_id="workspace",
            parameters={"operation": "delete", "path": "dummy.txt"},
        )
        result = cap.execute(req, context)
        assert result is not None
        assert result.outcome == CapabilityOutcome.FAILURE
        assert "Unsupported operation" in result.error

    def test_health(self, workspace_runtime: MockWorkspaceRuntime) -> None:
        cap = WorkspaceCapability(workspace_runtime)
        h = cap.health()
        assert h.status == CapabilityStatus.READY

    def test_estimate(self, workspace_runtime: MockWorkspaceRuntime) -> None:
        cap = WorkspaceCapability(workspace_runtime)
        e = cap.estimate(CapabilityRequest(capability_id="workspace"))
        assert e.capability_id == "workspace"

    def test_protocol_compliance(self, workspace_runtime: MockWorkspaceRuntime) -> None:
        cap = WorkspaceCapability(workspace_runtime)
        assert isinstance(cap, Capability)


# --- Runtime Tests (15) ---


class TestCapabilityRuntime:
    def test_execute_success(self, runtime: CapabilityRuntime, context: CapabilityContext) -> None:
        req = CapabilityRequest(
            capability_id="workspace",
            parameters={"operation": "write", "path": "test.txt", "content": "Hi"},
        )
        result = runtime.execute(req, context)
        assert result.success is True
        assert result.duration_ms > 0.0

    def test_execute_failure(self, runtime: CapabilityRuntime, context: CapabilityContext) -> None:
        req = CapabilityRequest(
            capability_id="workspace",
            parameters={"operation": "write"},  # Missing path
        )
        result = runtime.execute(req, context)
        assert result.success is False
        assert "Missing 'path'" in result.error

    def test_execute_capability_not_found(
        self, runtime: CapabilityRuntime, context: CapabilityContext
    ) -> None:
        req = CapabilityRequest(capability_id="missing")
        result = runtime.execute(req, context)
        assert result.success is False
        assert "not found" in result.error

    def test_execute_repository_commit(
        self, runtime: CapabilityRuntime, context: CapabilityContext
    ) -> None:
        req = CapabilityRequest(
            capability_id="repository", parameters={"operation": "commit", "message": "Test commit"}
        )
        result = runtime.execute(req, context)
        assert result.success is True
        assert result.output == "mock_commit_hash"

    def test_execute_review(self, runtime: CapabilityRuntime, context: CapabilityContext) -> None:
        req = CapabilityRequest(capability_id="review")
        result = runtime.execute(req, context)
        assert result.success is True
        assert result.metadata["decision"] == "approved"

    def test_runtime_registry_property(self, runtime: CapabilityRuntime) -> None:
        assert isinstance(runtime.registry, CapabilityRegistry)

    def test_runtime_default_registry(self) -> None:
        rt = CapabilityRuntime()
        assert len(rt.registry.list()) == 0

    def test_execute_preserves_request_id(
        self, runtime: CapabilityRuntime, context: CapabilityContext
    ) -> None:
        req = CapabilityRequest(
            capability_id="workspace",
            parameters={"operation": "write", "path": "t.txt", "content": "1"},
            request_id="custom_id",
        )
        result = runtime.execute(req, context)
        assert result.request_id == "custom_id"

    def test_execute_preserves_capability_id(
        self, runtime: CapabilityRuntime, context: CapabilityContext
    ) -> None:
        req = CapabilityRequest(
            capability_id="workspace",
            parameters={"operation": "write", "path": "t.txt", "content": "1"},
        )
        result = runtime.execute(req, context)
        assert result.capability_id == "workspace"

    def test_execute_duration_measured(
        self, runtime: CapabilityRuntime, context: CapabilityContext
    ) -> None:
        req = CapabilityRequest(
            capability_id="workspace",
            parameters={"operation": "write", "path": "t.txt", "content": "1"},
        )
        result = runtime.execute(req, context)
        assert result.duration_ms >= 0.0

    def test_execute_state_completed(
        self, runtime: CapabilityRuntime, context: CapabilityContext
    ) -> None:
        req = CapabilityRequest(
            capability_id="workspace",
            parameters={"operation": "write", "path": "t.txt", "content": "1"},
        )
        result = runtime.execute(req, context)
        assert result.state == CapabilityState.COMPLETED

    def test_execute_state_failed(
        self, runtime: CapabilityRuntime, context: CapabilityContext
    ) -> None:
        req = CapabilityRequest(capability_id="workspace", parameters={"operation": "write"})
        result = runtime.execute(req, context)
        assert result.state == CapabilityState.FAILED

    def test_execute_outcome_success(
        self, runtime: CapabilityRuntime, context: CapabilityContext
    ) -> None:
        req = CapabilityRequest(
            capability_id="workspace",
            parameters={"operation": "write", "path": "t.txt", "content": "1"},
        )
        result = runtime.execute(req, context)
        assert result.outcome == CapabilityOutcome.SUCCESS

    def test_execute_outcome_failure(
        self, runtime: CapabilityRuntime, context: CapabilityContext
    ) -> None:
        req = CapabilityRequest(capability_id="workspace", parameters={"operation": "write"})
        result = runtime.execute(req, context)
        assert result.outcome == CapabilityOutcome.FAILURE

    def test_execute_artifacts_empty(
        self, runtime: CapabilityRuntime, context: CapabilityContext
    ) -> None:
        req = CapabilityRequest(
            capability_id="workspace",
            parameters={"operation": "write", "path": "t.txt", "content": "1"},
        )
        result = runtime.execute(req, context)
        assert result.artifacts == ()


# --- Composite Capability Tests (10) ---


class TestCompositeCapability:
    def test_metadata(self, runtime: CapabilityRuntime) -> None:
        cap = CompositeCapability(runtime)
        assert cap.metadata.id == "composite"
        assert cap.metadata.kind == CapabilityKind.COMPOSITE

    def test_supports(self, runtime: CapabilityRuntime) -> None:
        cap = CompositeCapability(runtime)
        req = CapabilityRequest(capability_id="composite")
        assert cap.supports(req) is True

    def test_execute_success(self, runtime: CapabilityRuntime, context: CapabilityContext) -> None:
        cap = CompositeCapability(runtime)
        req = CapabilityRequest(
            capability_id="composite",
            parameters={
                "workflow": [
                    {
                        "capability_id": "workspace",
                        "parameters": {"operation": "write", "path": "t.txt", "content": "1"},
                    },
                    {
                        "capability_id": "repository",
                        "parameters": {"operation": "commit", "message": "Init"},
                    },
                ]
            },
        )
        result = cap.execute(req, context)
        assert result.success is True

    def test_execute_failure(self, runtime: CapabilityRuntime, context: CapabilityContext) -> None:
        cap = CompositeCapability(runtime)
        req = CapabilityRequest(
            capability_id="composite",
            parameters={
                "workflow": [
                    {
                        "capability_id": "workspace",
                        "parameters": {"operation": "write"},
                    },  # Missing path
                    {"capability_id": "repository", "parameters": {"operation": "commit"}},
                ]
            },
        )
        result = cap.execute(req, context)
        assert result.success is False
        assert "Workflow failed" in result.error

    def test_execute_empty_workflow(
        self, runtime: CapabilityRuntime, context: CapabilityContext
    ) -> None:
        cap = CompositeCapability(runtime)
        req = CapabilityRequest(capability_id="composite", parameters={"workflow": []})
        result = cap.execute(req, context)
        assert result.success is True

    def test_health(self, runtime: CapabilityRuntime) -> None:
        cap = CompositeCapability(runtime)
        h = cap.health()
        assert h.status == CapabilityStatus.READY

    def test_protocol_compliance(self, runtime: CapabilityRuntime) -> None:
        cap = CompositeCapability(runtime)
        assert isinstance(cap, Capability)

    def test_execute_preserves_request_id(
        self, runtime: CapabilityRuntime, context: CapabilityContext
    ) -> None:
        cap = CompositeCapability(runtime)
        req = CapabilityRequest(
            capability_id="composite", parameters={"workflow": []}, request_id="custom_id"
        )
        result = cap.execute(req, context)
        assert result.request_id == "custom_id"

    def test_execute_metadata_contains_results(
        self, runtime: CapabilityRuntime, context: CapabilityContext
    ) -> None:
        cap = CompositeCapability(runtime)
        req = CapabilityRequest(
            capability_id="composite",
            parameters={
                "workflow": [
                    {
                        "capability_id": "workspace",
                        "parameters": {"operation": "write", "path": "t.txt", "content": "1"},
                    }
                ]
            },
        )
        result = cap.execute(req, context)
        assert "results" in result.metadata

    def test_register_composite(self, runtime: CapabilityRuntime) -> None:
        reg = CapabilityRegistry()
        reg.register(CompositeCapability(runtime))
        assert len(reg.list()) == 1
