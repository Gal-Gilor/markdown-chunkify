import subprocess
import sys

import markdown_chunkify
from markdown_chunkify import models
from markdown_chunkify import splitter


def test_star_import():
    """`from markdown_chunkify import *` imports every name in `__all__`."""
    result = subprocess.run(
        [sys.executable, "-c", "from markdown_chunkify import *"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr


def test_models_exported_from_package():
    """Section and SectionMetadata are importable from the package root."""
    assert markdown_chunkify.Section is models.Section
    assert markdown_chunkify.SectionMetadata is models.SectionMetadata
    assert {"Section", "SectionMetadata"} <= set(markdown_chunkify.__all__)


def test_splitter_exported_from_package():
    """MarkdownSplitter is importable from the package root."""
    assert markdown_chunkify.MarkdownSplitter is splitter.MarkdownSplitter
    assert "MarkdownSplitter" in markdown_chunkify.__all__
