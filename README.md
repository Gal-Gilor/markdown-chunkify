[![Execute Tests](https://github.com/Gal-Gilor/markdown-chunkify/actions/workflows/execute_main_tests.yaml/badge.svg)](https://github.com/Gal-Gilor/markdown-chunkify/actions/workflows/execute_main_tests.yaml)

# MarkdownSplitter

A Python library that splits Markdown into hierarchical sections. It keeps code blocks intact, tracks parent-child and sibling relationships between sections, can transliterate Unicode to ASCII, and can optionally convert PDFs to Markdown.

## Features

- Lines inside fenced code blocks (```` ``` ```` or `~~~`, including fences in list items), HTML comment blocks and YAML front matter are never treated as headers. Section text keeps them exactly as written
- Splits on headers from H1 to H6. `MarkdownSplitter(max_level=3)` keeps deeper headers as text of the enclosing section
- Tracks parent headers and siblings for each section. Headers with the same text are kept as separate sections. `MarkdownSplitter(max_siblings=10)` lists only the 10 nearest siblings
- Text before the first header, or a document without headers, is returned as a level-0 section with an empty header
- Records where each section is in the source text. `text[start:end]` with `start, end = section.metadata.span` returns the section's header line and text as written, and `metadata.char_count` is its length
- Keeps the source text by default. `normalize_unicode=True` transliterates headers and text to ASCII (`Café` becomes `Cafe`)
- Optional extra: PDF to Markdown conversion (`pdf`)

## Installation

```bash
pip install "markdown-chunkify @ git+https://github.com/Gal-Gilor/markdown-chunkify.git"
```

The splitter depends on Pydantic and [anyascii](https://github.com/anyascii/anyascii). Install the `pdf` extra for the PDF parser:
```bash
pip install "markdown-chunkify[pdf] @ git+https://github.com/Gal-Gilor/markdown-chunkify.git"
```

The `pdf` extra installs [PyMuPDF](https://github.com/pymupdf/PyMuPDF) through `pymupdf4llm`. PyMuPDF is licensed under the AGPL-3.0 or an Artifex commercial license, unlike this package's Apache-2.0 license.

For Development Setup (requires [uv](https://docs.astral.sh/uv/)):
```bash
git clone https://github.com/Gal-Gilor/markdown-chunkify.git
cd markdown-chunkify
uv sync --all-extras
uv run pytest -vv
uv run ruff check .
uv run ruff format .
```

The [Execute Tests](.github/workflows/execute_main_tests.yaml) workflow runs Ruff, the tests on Python 3.12 and 3.13, and a wheel build on pushes and pull requests to `main`.

## Usage

```python
from markdown_chunkify import MarkdownSplitter

# Initialize splitter
splitter = MarkdownSplitter()

# Split from text
sections = splitter.split_text(markdown_text)

# Split from file
sections = splitter.split_file("document.md")

# Nested outline instead of a flat list
outline = splitter.get_document_outline(markdown_text)
```

Convert a PDF to Markdown (`pdf` extra):
```python
from markdown_chunkify import PyMuPDFMParser

# Returns the Markdown and saves it as output/report.md
markdown_text = PyMuPDFMParser.to_markdown(
    file_path="docs/report.pdf",
    destination_path="output",  # Optional
)
```

### Unicode normalization

With `normalize_unicode=True`, `split_text` and `split_file` transliterate each section's header and text to ASCII with [anyascii](https://github.com/anyascii/anyascii). The parents and siblings use the transliterated headers. It is off by default.
```python
text = "# Café\nnaïve — “quoted”"

splitter.split_text(text)[0].section_text  # 'naïve — “quoted”'
splitter.split_text(text, normalize_unicode=True)[0].section_text  # 'naive - "quoted"'
```

Transliteration also rewrites text that has no Latin form: `Привет` becomes `Privet`, `北京` becomes `BeiJing` and emoji become names such as `:grinning:`. Code blocks are transliterated too, so `x = "é"` becomes `x = "e"`.

Leave it off when you extract entities for a knowledge graph. Transliteration changes entity names (`Müller GmbH` becomes `Muller GmbH`), so entities extracted from normalized text no longer match the source document or other sources that keep the original spelling. It suits pipelines that need ASCII-only text, such as a search index with an ASCII tokenizer.

Headers are found before the text is transliterated, so spans still point at the source text and a fullwidth `＃` does not become a header. `metadata.normalized` is `True` for sections whose header or text changed. `get_document_outline` always returns the source text.

### Limitations

- Only ATX headers (`#` to `######`) are recognized. Setext headers, underlined with `===` or `---`, stay in the section text.
- Headers and fences inside blockquotes (`> # Title`) are not recognized.
- A line indented by 4 or more spaces that starts with ```` ``` ```` or `~~~` is treated as a fence, even inside an indented code block. If that fence is never closed, the headers after it are treated as text and a warning is logged.
- An HTML comment is only recognized when `<!--` starts the line. A comment that opens mid-line (`text <!--`) does not hide the `#` lines inside it.
- A document that starts with `---` is treated as having YAML front matter only if the line after it is a `key:` entry and every line up to the next `---` or `...` looks like YAML (`key: value`, `- item`, indented lines, comments or blank lines). Otherwise the `---` is a horizontal rule and the headers after it are split as usual.
- Without `max_siblings`, each section lists every other header at its level under the same parent. With n such headers, the lists hold n * (n - 1) names: 6,000 headers at one level take a few seconds to split. Set `max_siblings` for documents like that.

## Data Models

`Section` and `SectionMetadata` are exported from the package root:
```python
from markdown_chunkify import Section
from markdown_chunkify import SectionMetadata
```

**MarkdownContent:** The base data structure representing a Markdown section. It contains the header and content of a section and is the base class of the `Section` model.
```python
class MarkdownContent(BaseModel):
    section_header: str  # The header of the section (without #)
    section_text: str  # The content of the section
```

**Section:** The primary data structure representing a Markdown section. It contains the header level, metadata, and content of a section.
```python
class Section(MarkdownContent):
    # Number of # symbols (1-6), 0 for text before the first header
    header_level: int
    # Normalization and hierarchy information
    metadata: SectionMetadata

    # Convert the section back to Markdown
    def to_markdown(self) -> str: ...
```

**SectionMetadata:** A Section's metadata: whether Unicode normalization changed it, its parent and sibling headers, and where it is in the source text.
```python
class SectionMetadata(BaseModel):
    # Whether Unicode normalization changed the header or text
    normalized: bool
    # Parent headers by level, such as {"h1": "Guide", "h2": "Install"}
    parents: dict[str, str | None]
    # Headers at the same level with the same parent
    siblings: list[str]
    # Start (inclusive) and end (exclusive) offsets in the source text
    span: tuple[int, int] | None
    # Number of characters in the span
    char_count: int | None
```

The span starts at the header line and ends at the last non-whitespace character of the section text. It does not include subsections, leading blank lines or trailing whitespace. Offsets count characters in the string passed to `split_text`, including a byte order mark. A normalized section keeps the span and character count of the source text, so `text[start:end]` returns the text before transliteration.

### Methods

- `to_markdown()`: Convert to Markdown format

## Requirements
- Python 3.12+

## License
Apache License 2.0 - See [LICENSE](LICENSE)