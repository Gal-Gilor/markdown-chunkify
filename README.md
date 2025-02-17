# MarkdownSplitter

A Python library that splits Markdown into hierarchical sections. It intelligently handles code blocks, normalizes Unicode characters, and maintains parent-child relationships between sections.

## Features

- **Code-Aware**: Preserves code blocks and comments while processing markdown
- **Hierarchy Tracking**: Automatically tracks parent headers for each section (H1-H4)
- **Unicode Normalization**: Converts non-ASCII characters to their ASCII equivalents

## Installation

```bash
pip install -e .
```

For Development Setup:
```bash
git clone https://github.com/Gal-Gilor/markdown-chunkify.git
cd markdown-chunkify
poetry install
poetry run pytest tests -vv
```

## Configuration

### Environment Variables

The following environment variables are required for the `UnicodeReplaceProcessor` component.

| Variable | Description | Default |
|----------|-------------|---------|
| `GOOGLE_API_KEY` | A Gemini API key | `None` |
| `GEMINI_MODEL_NAME` | A Gemini model name | `gemini-2.0-flash` | 


## Usage

```python
from markdown_chunkify import MarkdownSplitter
from markdown_chunkify import PyMuPDFMParser


# Convert PDF to Markdown
markdown_text = PyMuPDFMParser.to_markdown(
    file_path="document.pdf",
    destination_path="document.md"  # Optional
)

# Initialize splitter
splitter = MarkdownSplitter()

# Split from file
sections = splitter.from_file('document.md')

# Split from text
sections = splitter.split_text(markdown_text)
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
    header_level: int                           # Number of # symbols (1-4)
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
```

### Methods

- `to_markdown()`: Convert to Markdown format

## Requirements
- Python 3.12+

## License
Apache License 2.0 - See [LICENSE](LICENSE)