"""Domain model for the EBS-014 article API fixture."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Article:
    """A public article representation returned by the list endpoint."""

    identifier: int
    title: str
