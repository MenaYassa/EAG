from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path

_STATIC_PAGE = Path(__file__).parents[1] / "src/eag/governed_visual_presentation/static/index.html"
_STATIC_CSS = Path(__file__).parents[1] / "src/eag/governed_visual_presentation/static/app.css"


class _PageStructure(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.elements: list[tuple[str, dict[str, str]]] = []
        self.text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.elements.append((tag, {key: value or "" for key, value in attrs}))

    def handle_data(self, data: str) -> None:
        normalized = " ".join(data.split())
        if normalized:
            self.text.append(normalized)


def _page() -> _PageStructure:
    parser = _PageStructure()
    parser.feed(_STATIC_PAGE.read_text(encoding="utf-8"))
    return parser


def _element_by_id(parser: _PageStructure, element_id: str) -> tuple[str, dict[str, str]]:
    return next(element for element in parser.elements if element[1].get("id") == element_id)


def test_four_stage_workflow_hierarchy_uses_semantic_static_structure() -> None:
    parser = _page()
    visible_text = "\n".join(parser.text)

    assert [text for text in parser.text if text in {
        "Prepare locally",
        "Review prepared inputs",
        "Explicitly submit governed construction",
        "Review terminal result",
    }] == [
        "Prepare locally",
        "Review prepared inputs",
        "Explicitly submit governed construction",
        "Review terminal result",
    ]
    assert sum(1 for tag, attrs in parser.elements if tag == "form" and attrs.get("id") == "construct-form") == 1
    assert sum(1 for tag, _ in parser.elements if tag == "fieldset") == 2
    assert "Local preparation does not submit." in visible_text
    assert "Create is the sole explicit governed submission action." in visible_text
    assert "Review returned terminal facts and receipt-backed file details." in visible_text


def test_existing_control_contracts_and_result_targets_are_preserved() -> None:
    parser = _page()

    expected_ids = {
        "submission-manifest",
        "clear-selected-manifest",
        "pasted-manifest",
        "clear-pasted-manifest",
        "load-pasted-manifest",
        "discard-prepared-inputs",
        "import-status",
        "dismiss-import-status",
        "profile",
        "status",
        "dismiss-terminal-result",
        "facts",
        "files",
    }
    assert expected_ids <= {attrs["id"] for _, attrs in parser.elements if "id" in attrs}
    assert _element_by_id(parser, "submission-manifest") == (
        "input",
        {"id": "submission-manifest", "type": "file", "accept": "application/json"},
    )
    assert _element_by_id(parser, "pasted-manifest")[0] == "textarea"
    assert _element_by_id(parser, "profile")[1]["name"] == "profile"
    assert _element_by_id(parser, "profile")[1]["readonly"] == ""
    assert _element_by_id(parser, "import-status")[1]["aria-live"] == "polite"
    assert _element_by_id(parser, "status")[1] == {"id": "status"}
    assert _element_by_id(parser, "files")[1] == {"id": "files", "hidden": ""}

    buttons = [attrs for tag, attrs in parser.elements if tag == "button"]
    local_button_ids = {
        "clear-selected-manifest",
        "clear-pasted-manifest",
        "load-pasted-manifest",
        "discard-prepared-inputs",
        "dismiss-import-status",
        "dismiss-terminal-result",
    }
    assert {attrs["id"] for attrs in buttons if "id" in attrs} >= local_button_ids
    assert all(_element_by_id(parser, button_id)[1]["type"] == "button" for button_id in local_button_ids)
    submit_buttons = [attrs for attrs in buttons if attrs.get("type") == "submit"]
    assert submit_buttons == [{"class": "primary-action", "type": "submit"}]


def test_first_party_css_defines_hierarchy_focus_and_narrow_viewport_without_frameworks() -> None:
    css = _STATIC_CSS.read_text(encoding="utf-8")

    for selector in (
        ".workflow-form",
        ".workflow-stage",
        ".source-grid",
        ".local-action-row",
        ".primary-submit-area",
        ".primary-action",
        ".result-card",
        "button:focus-visible",
        "@media (max-width: 720px)",
    ):
        assert selector in css
    assert "grid-template-columns: 1fr;" in css
    assert "outline: 3px solid #5eead4;" in css
    for forbidden in ("@import", "tailwind", "bootstrap", "react", "vue", "svelte", "url("):
        assert forbidden not in css.lower()
