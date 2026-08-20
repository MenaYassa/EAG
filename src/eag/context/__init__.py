"""Read-only repository context assembly for governed engineering decisions."""

from eag.context.facades import (
    ProvidedVcsReadFacade,
    RepositoryDiscoveryFacade,
    UnavailableVcsReadFacade,
    VcsReadFacade,
)
from eag.context.models import (
    CONTEXT_CONTRACT_VERSION,
    CONTEXT_POLICY_VERSION,
    ContextAssemblyError,
    ContextBudget,
    ContextFingerprint,
    ContextProvenanceRecord,
    ContextTruncationReport,
    DependencyReference,
    FileReference,
    RepositoryContextSnapshot,
    RepositorySnapshotFingerprint,
    RepositoryStateEvidence,
    SelectedRepositoryContext,
    SourceArtifactRecord,
    SourceExcerpt,
    StaleContextError,
    SymbolReference,
)
from eag.context.runtime import (
    RepositoryContextAssembler,
    create_repository_context_assembler,
)
from eag.context.selection import ContextSelector
from eag.context.sensitivity import (
    ContextSecurityPolicy,
    SanitizedContent,
    SensitivityDecision,
)

__all__ = [
    "CONTEXT_CONTRACT_VERSION",
    "CONTEXT_POLICY_VERSION",
    "ContextAssemblyError",
    "ContextBudget",
    "ContextFingerprint",
    "ContextProvenanceRecord",
    "ContextSecurityPolicy",
    "ContextSelector",
    "ContextTruncationReport",
    "DependencyReference",
    "FileReference",
    "RepositoryContextAssembler",
    "RepositoryContextSnapshot",
    "ProvidedVcsReadFacade",
    "RepositoryDiscoveryFacade",
    "RepositorySnapshotFingerprint",
    "RepositoryStateEvidence",
    "SanitizedContent",
    "SelectedRepositoryContext",
    "SensitivityDecision",
    "SourceArtifactRecord",
    "SourceExcerpt",
    "StaleContextError",
    "SymbolReference",
    "UnavailableVcsReadFacade",
    "VcsReadFacade",
    "create_repository_context_assembler",
]
