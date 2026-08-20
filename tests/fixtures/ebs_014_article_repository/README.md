# EBS-014 Article API Fixture

This fixture is an independent, read-only article-list API used to evaluate repository-aware advisory decisions. The public list endpoint delegates to `article_app.service.list_articles`; its response contract is a JSON-style list. Pagination must preserve that list response shape and extend the existing endpoint tests.
