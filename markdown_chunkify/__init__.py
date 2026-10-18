import importlib
import logging

from markdown_chunkify.components.splitters import MarkdownSplitter
from markdown_chunkify.core.models import OutlineNode
from markdown_chunkify.core.models import Section
from markdown_chunkify.core.models import SectionMetadata

logging.getLogger(__name__).addHandler(logging.NullHandler())

# Components that need an optional extra are imported on first access.
_OPTIONAL_COMPONENTS = {
    "PyMuPDFMParser": ("markdown_chunkify.components.parsers", "pdf"),
}


def __getattr__(name: str):
    if name not in _OPTIONAL_COMPONENTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module_name, extra = _OPTIONAL_COMPONENTS[name]
    try:
        module = importlib.import_module(module_name)
    except ImportError as e:
        raise ImportError(
            f"{name} requires the '{extra}' extra. "
            f"Install it with: pip install 'markdown-chunkify[{extra}]'"
        ) from e

    return getattr(module, name)


__all__ = [
    "MarkdownSplitter",
    "OutlineNode",
    "PyMuPDFMParser",
    "Section",
    "SectionMetadata",
]
