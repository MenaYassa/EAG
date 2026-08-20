"""Public route boundary for the EBS-014 article API fixture."""

from article_app.service import list_articles


def get_articles() -> list[dict[str, object]]:
    """Return the existing JSON-style list response without pagination metadata."""
    return [
        {"identifier": article.identifier, "title": article.title}
        for article in list_articles()
    ]
