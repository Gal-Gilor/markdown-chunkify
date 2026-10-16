# MarkdownSplitter

A Python library that splits Markdown into hierarchical sections. It keeps code blocks intact, tracks parent-child and sibling relationships between sections, and can optionally convert PDFs to Markdown and normalize Unicode characters with Gemini.

## Features

- Lines inside fenced code blocks (```` ``` ```` or `~~~`) are never treated as headers, and section text keeps code blocks exactly as written
- Splits on headers from H1 to H6. `MarkdownSplitter(max_level=3)` keeps deeper headers as text of the enclosing section
- Tracks parent headers and siblings for each section. Headers with the same text are kept as separate sections
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

For Development Setup:
```bash
git clone https://github.com/Gal-Gilor/markdown-chunkify.git
cd markdown-chunkify
poetry install --all-extras
poetry run pytest tests -vv
```

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

markdown_text = PyMuPDFMParser.to_markdown(file_path="document.pdf")
```

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