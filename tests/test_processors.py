import json
from types import SimpleNamespace

import pytest

pytest.importorskip("google.genai")

from markdown_chunkify.components.processors import UnicodeReplaceProcessor  # noqa: E402
from markdown_chunkify.core.models import Section  # noqa: E402
from markdown_chunkify.core.models import SectionMetadata  # noqa: E402


def _response(section_header: str, section_text: str) -> SimpleNamespace:
    """A stand-in for a Gemini response with the fields the processor reads."""
    usage = {"usage_metadata": {"candidates_token_count": 7}, "model_version": "test"}
    return SimpleNamespace(
        text=json.dumps({"section_header": section_header, "section_text": section_text}),
        to_json_dict=lambda: usage,
    )


@pytest.fixture
def section():
    return Section(
        section_header="Cafe",
        section_text="Café menu",
        header_level=2,
        metadata=SectionMetadata(parents={"h1": "Places"}, siblings=["Bar", "Diner"]),
    )


def test_normalized_section_keeps_hierarchy(section):
    """The normalized section keeps its parents and siblings."""
    processor = UnicodeReplaceProcessor(client=None)
    normalized = processor._create_normalized_section(_response("Cafe", "Cafe menu"), section)

    assert normalized.metadata.normalized is True
    assert normalized.section_text == "Cafe menu"
    assert normalized.metadata.parents == {"h1": "Places"}
    assert normalized.metadata.siblings == ["Bar", "Diner"]


@pytest.mark.parametrize(
    "response_header, expected_header",
    [("## Cafe", "Cafe"), ("Cafe", "Cafe"), ("# Cafe", "# Cafe")],
)
def test_normalized_header_strips_own_markers(section, response_header, expected_header):
    """Only the section's own '#' markers are stripped from the model's header."""
    processor = UnicodeReplaceProcessor(client=None)
    normalized = processor._create_normalized_section(
        _response(response_header, "Cafe menu"), section
    )

    assert normalized.section_header == expected_header
