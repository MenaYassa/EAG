"""G2.4.23 thin receipt-backed local terminal presentation boundary."""

from eag.governed_presentation.fixed_profile import (
    FixedProfilePresentationDisposition,
    FixedProfilePresentationFailureStage,
    FixedProfilePresentationSubmission,
    FixedProfileTerminalView,
    TerminalReceiptFile,
    continue_fixed_profile_after_handoff,
    render_fixed_profile_terminal_view,
    submit_fixed_profile_construction,
)

__all__ = [
    "FixedProfilePresentationDisposition",
    "continue_fixed_profile_after_handoff",
    "FixedProfilePresentationFailureStage",
    "FixedProfilePresentationSubmission",
    "FixedProfileTerminalView",
    "TerminalReceiptFile",
    "render_fixed_profile_terminal_view",
    "submit_fixed_profile_construction",
]
