"""Article-list domain service for the EBS-014 fixture."""

from __future__ import annotations

from article_app.models import Article

_ARTICLES = (
    Article(identifier=1, title="Repository intelligence"),
    Article(identifier=2, title="Governed decisions"),
)


def list_articles() -> list[Article]:
    """Return the complete list while preserving the public list response contract."""
    return list(_ARTICLES)
