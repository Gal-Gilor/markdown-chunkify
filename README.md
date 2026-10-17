[![Execute Tests](https://github.com/Gal-Gilor/markdown-chunkify/actions/workflows/execute_main_tests.yaml/badge.svg)](https://github.com/Gal-Gilor/markdown-chunkify/actions/workflows/execute_main_tests.yaml)

# MarkdownSplitter

A Python library that splits Markdown into hierarchical sections. It keeps code blocks intact, tracks parent-child and sibling relationships between sections, and can optionally convert PDFs to Markdown and normalize Unicode characters with Gemini.

## Features

- Lines inside fenced code blocks (```` ``` ```` or `~~~`, including fences in list items), HTML comment blocks and YAML front matter are never treated as headers. Section text keeps them exactly as written
- Splits on headers from H1 to H6. `MarkdownSplitter(max_level=3)` keeps deeper headers as text of the enclosing section
- Tracks parent headers and siblings for each section. Headers with the same text are kept as separate sections. `MarkdownSplitter(max_siblings=10)` lists only the 10 nearest siblings
- Text before the first header, or a document without headers, is returned as a level-0 section with an empty header
- Optional extras: PDF to Markdown conversion (`pdf`) and Gemini-powered Unicode normalization (`normalize`)

## Installation

```bash
pip install "markdown-chunkify @ git+https://github.com/Gal-Gilor/markdown-chunkify.git"
```

The splitter only depends on Pydantic. Install the extras for the PDF parser or the Unicode normalizer:
```bash
pip install "markdown-chunkify[pdf] @ git+https://github.com/Gal-Gilor/markdown-chunkify.git"
pip install "markdown-chunkify[normalize] @ git+https://github.com/Gal-Gilor/markdown-chunkify.git"
```

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

## Configuration

### Environment Variables

The following environment variables are used by the `UnicodeReplaceProcessor` component (`normalize` extra).

| Variable | Description | Default |
|----------|-------------|---------|
| `GOOGLE_API_KEY` | A Gemini API key | `None` |
| `GOOGLE_GEMINI_MODEL` | A Gemini model name | `gemini-2.0-flash` | 


## Usage

```python
from markdown_chunkify import MarkdownSplitter

# Initialize splitter
splitter = MarkdownSplitter()

# Split from text
sections = splitter.split_text(markdown_text)

# Split from file
sections = MarkdownSplitter.from_file("document.md")

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

Replace non-ASCII characters in each section with their closest ASCII equivalents (`normalize` extra). This makes one Gemini API call per section:
```python
from google import genai

from markdown_chunkify import MarkdownSplitter
from markdown_chunkify import UnicodeReplaceProcessor

client = genai.Client()  # Reads the API key from GOOGLE_API_KEY
processor = UnicodeReplaceProcessor(client=client)

sections = MarkdownSplitter().split_text(markdown_text)
normalized_sections = [processor.process_text(section) for section in sections]
```

A normalized section has `metadata.normalized` set to `True` and keeps the original header and text in `metadata.original_content`. If a call fails, the original section is returned with the error in `metadata.error`.

### Limitations

- Only ATX headers (`#` to `######`) are recognized. Setext headers, underlined with `===` or `---`, stay in the section text.
- Headers and fences inside blockquotes (`> # Title`) are not recognized.
- A line indented by 4 or more spaces that starts with ```` ``` ```` or `~~~` is treated as a fence, even inside an indented code block. If that fence is never closed, the headers after it are treated as text and a warning is logged.
- An HTML comment is only recognized when `<!--` starts the line. A comment that opens mid-line (`text <!--`) does not hide the `#` lines inside it.
- A document that starts with `---` is treated as having YAML front matter only if the line after it is a `key:` entry and every line up to the next `---` or `...` looks like YAML (`key: value`, `- item`, indented lines, comments or blank lines). Otherwise the `---` is a horizontal rule and the headers after it are split as usual.
- Without `max_siblings`, each section lists every other header at its level under the same parent. With n such headers, the lists hold n * (n - 1) names: 6,000 headers at one level take a few seconds to split. Set `max_siblings` for documents like that.

## Data Models

**MarkdownContent:** The base data structure representing a Markdown section. It contains the header and content of a section. It's used as a base class for the `Section` model, and as a generation schema for structured output responses
```python
class MarkdownContent(BaseModel):
    section_header: str                         # The header of the section (without #)
    section_text: str                           # The content of the section
```

**Section:** The primary data structure representing a Markdown section. It contains the header level, metadata, and content of a section.
```python
class Section(MarkdownContent):
    header_level: int                           # Number of # symbols (1-6), 0 for text before the first header
    metadata: SectionMetadata                   # Processing and hierarchy information

    def to_markdown(self) -> str:               # Convert section back to Markdown
```

**SectionMetadata:** A Section's metadata, containing information about the section's processing and hierarchy (i.e., from information about the parent headers and text normalization status).
```python
class SectionMetadata(BaseModel):
    token_count: int | None                     # Generation token count
    model_version: str | None                   # Model used for normalization
    normalized: bool                            # Whether Unicode normalization succeeded
    error: str | None                           # Error message if normalization failed
    original_content: MarkdownContent | None    # Pre-normalization content
    parents: dict[str, str | None]              # Header hierarchy information
    siblings: list[str]                         # Headers at the same level with the same parent
```

### Methods

- `to_markdown()`: Convert to Markdown format

## Requirements
- Python 3.12+

## License
Apache License 2.0 - See [LICENSE](LICENSE)