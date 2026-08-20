"""Existing contract tests for the EBS-014 article API fixture."""

from article_app.routes import get_articles


def test_get_articles_returns_a_list_of_article_records() -> None:
    response = get_articles()
    assert isinstance(response, list)
    assert response
    assert response[0] == {"identifier": 1, "title": "Repository intelligence"}
