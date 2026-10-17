import subprocess
import sys

import pytest

import markdown_chunkify
from markdown_chunkify.core import models


def _run(code: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)


def test_core_import_skips_optional_dependencies():
    """Importing the splitter and models does not load the PDF dependencies.

    The Gemini dependencies were removed and are checked so they are not added back.
    """
    result = _run(
        "import sys\n"
        "from markdown_chunkify import MarkdownSplitter, Section, SectionMetadata\n"
        "loaded = {'google', 'pymupdf4llm', 'jinja2', 'tenacity'} & set(sys.modules)\n"
        "assert not loaded, loaded\n"
    )

    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    "name, blocked_module, extra",
    [
        ("PyMuPDFMParser", "pymupdf4llm", "pdf"),
    ],
)
def test_missing_extra_names_the_extra(name, blocked_module, extra):
    """Accessing a component without its extra raises an ImportError naming the extra."""
    result = _run(
        "import sys\n"
        f"sys.modules[{blocked_module!r}] = None\n"
        "import markdown_chunkify\n"
        f"markdown_chunkify.{name}\n"
    )

    assert result.returncode != 0
    assert f"markdown-chunkify[{extra}]" in result.stderr


def test_models_exported_from_package():
    """Section and SectionMetadata are importable from the package root."""
    assert markdown_chunkify.Section is models.Section
    assert markdown_chunkify.SectionMetadata is models.SectionMetadata
    assert {"Section", "SectionMetadata"} <= set(markdown_chunkify.__all__)
