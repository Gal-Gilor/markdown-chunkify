import importlib

from markdown_chunkify.components.splitters import MarkdownSplitter

# Components that need an optional extra are imported on first access.
_OPTIONAL_COMPONENTS = {
    "PyMuPDFMParser": ("markdown_chunkify.components.parsers", "pdf"),
    "UnicodeReplaceProcessor": ("markdown_chunkify.components.processors", "normalize"),
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


__all__ = ["MarkdownSplitter", "PyMuPDFMParser", "UnicodeReplaceProcessor"]
