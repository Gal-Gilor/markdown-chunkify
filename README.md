# Markdown Chunkify

A Python library for intelligently splitting Markdown documents into hierarchical sections while preserving their header structure and parent-child relationships. Perfect for processing large markdown documents or creating semantic chunks for document analysis.

## Features

- Split markdown documents into structured sections based on headers
- Preserve complete header hierarchy (h1-h4)
- Track parent-child relationships between sections
- Clean, typed API using dataclasses
- Support for both string and file inputs
- Full test coverage
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

## License

Apache License 2.0 - See [LICENSE](LICENSE) for details.