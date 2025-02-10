# Markdown Chunkify

A Python library for intelligently splitting Markdown documents into hierarchical sections while preserving their header structure and parent-child relationships. Perfect for processing large markdown documents or creating semantic chunks for document analysis.

## Features

- Split markdown documents into structured sections based on headers
- Preserve complete header hierarchy (h1-h4)
- Track parent-child relationships between sections
- Support for both Markdown string and file inputs
- Python 3.12+ support

## Installation

From source
```bash
pip install -e .
```

### Usage

```python
from markdown_chunkify import MarkdownSplitter

splitter = MarkdownSplitter()
readme_chunks = splitter.from_file("../README.md")
sections_dict = [section.to_dict() for section in readme_chunks]
print(sections_dict[0])
```

First Section Output:
```json
{
  "section_header": "Markdown Chunkify",
  "section_text": "A Python library for intelligently splitting Markdown documents into hierarchical sections while preserving their header structure and parent-child relationships. Perfect for processing large markdown documents or creating semantic chunks for document analysis.",
  "header_level": 1,
  "metadata": {
    "parents": {}
  }
}
```

## Requirements

- Python 3.12+

## Development

Clone the repository:
```bash
git clone https://github.com/Gal-Gilor/markdown-chunkify.git
cd markdown-chunkify
```

Install Dependencies:
If Poetry is not installed, see [Poetry Installation](https://python-poetry.org/docs/#installation)
```bash
poetry install
```

Run tests:
```bash
poetry run pytest
```

## Core Components

### MarkdownSection

The `MarkdownSection` class is the fundamental data structure that represents a section of a Markdown document. It maintains both the content and hierarchical structure of the document.

```python
@dataclass
class MarkdownSection:
    section_header: str       # The header text (without # symbols)
    section_text: str        # The content below the header
    header_level: int        # Number of # symbols (1-6)
    metadata: dict          # Contains hierarchical information
```

#### Features

- **Header Hierarchy**: Tracks parent headers up to 4 levels (h1-h4)
- **Flexible Creation**: Use the `create()` factory method for proper instantiation
- **Multiple Export Formats**:
  - Convert to dictionary with `to_dict()`
  - Convert back to Markdown with `to_markdown()`
  - Pretty-printed JSON representation via `str()`

## License

Apache License 2.0 - See [LICENSE](LICENSE) for details.
