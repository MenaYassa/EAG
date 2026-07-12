from dataclasses import dataclass


def _validate_non_negative_int(value: int, field_name: str) -> int:
    if not isinstance(value, int) or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer")
    return value


@dataclass(frozen=True, slots=True, kw_only=True)
class AnalysisMetrics:
    lines: int = 0
    blank_lines: int = 0
    comment_lines: int = 0
    symbols: int = 0
    dependencies: int = 0

    def __post_init__(self) -> None:
        _validate_non_negative_int(self.lines, "lines")
        _validate_non_negative_int(self.blank_lines, "blank_lines")
        _validate_non_negative_int(self.comment_lines, "comment_lines")
        _validate_non_negative_int(self.symbols, "symbols")
        _validate_non_negative_int(self.dependencies, "dependencies")
