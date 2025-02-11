# MarkdownSplitter

A Python library that splits Markdown into hierarchical sections. It intelligently handles code blocks, and maintains references to the section's parent headers, making it easier to manage and analyze, and embed Markdown text.

## Why MarkdownSplitter?

- **Code-Aware**: Prevents splitting text wrapped in code blocks, ensuring content integrity.
- **Hierarchy Tracking**: Automatically tracks and stores parent headers for each section.

## Installation

```bash
pip install -e .
```

For development setup:
```bash
git clone https://github.com/Gal-Gilor/markdown-chunkify.git
cd markdown-chunkify
poetry install
poetry run pytest /tests -vv
```

## Usage

```python
from markdown_splitter import MarkdownSplitter


splitter = MarkdownSplitter()

# From file
sections = MarkdownSplitter.from_file('document.md')
# From text
sections = splitter.split_text(text)
```

## MarkdownSection

The fundamental data structure representing a Markdown section:

```python
@dataclass
class MarkdownSection:
    section_header: str         # Header text (without #)
    section_text: str           # Content below header
    header_level: int           # Number of # symbols (1-4)
    metadata: dict[str, str]    # Hierarchical information
```

### Metadata Structure

Parent headers are tracked in `metadata['parents']`:
```python
{
    'h1': 'Parent H1 Header',
    'h2': 'Parent H2 Header',
    # ... up to h4
}
```

### Methods
- `create()`: Factory method for proper instantiation
- `to_dict()`: Convert to dictionary
- `to_markdown()`: Convert to Markdown format

## Requirements
- Python 3.12+

## License
Apache License 2.0 - See [LICENSE](LICENSE)