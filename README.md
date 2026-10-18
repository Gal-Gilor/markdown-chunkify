[![Lint, test and build](https://github.com/Gal-Gilor/markdown-chunkify/actions/workflows/lint-test-build.yaml/badge.svg)](https://github.com/Gal-Gilor/markdown-chunkify/actions/workflows/lint-test-build.yaml) [![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/Gal-Gilor/markdown-chunkify)

# MarkdownSplitter

A Python library that splits Markdown into hierarchical sections. It keeps code blocks intact, links each section to its parent section, can transliterate Unicode to ASCII, and can optionally convert PDFs to Markdown.

## Features

- Lines inside fenced code blocks (```` ``` ```` or `~~~`, including fences in list items), HTML comment blocks, `<pre>`, `<script>`, `<style>` and `<textarea>` blocks and YAML front matter are never treated as headers. Section text keeps them exactly as written
- Splits on headers from H1 to H6. `MarkdownSplitter(max_level=3)` keeps deeper headers as text of the enclosing section
- Gives each section an id and its parent section's id, so the header hierarchy can be rebuilt as a tree or loaded into a graph. Headers with the same text are kept as separate sections
- Text before the first header, or a document without headers, is returned as a level-0 section with an empty header
- `section.breadcrumb()` returns the section's header path, such as `Docker > Installation`, to send with the section text to an embedding model or LLM
- Records where each section is in the source text. `text[start:end]` with `start, end = section.metadata.span` returns the section's header line and text as written. `metadata.char_count` is the length of that span, not of `section_text` or `to_markdown()`
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

The [Lint, test and build](.github/workflows/lint-test-build.yaml) workflow runs Ruff, the tests on Python 3.12, 3.13 and 3.14, and a wheel build on pushes and pull requests to `main`.

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

### Section ids and parents

`metadata.id` is the section's position in document order, starting at 0, so `sections[i].metadata.id == i`. `metadata.parent_id` is the id of the enclosing section, or `None` for top-level sections and text before the first header.
```python
text = "# Docker\n## Installation\n## Usage\n# Kubernetes"
sections = splitter.split_text(text)

[(s.section_header, s.metadata.id, s.metadata.parent_id) for s in sections]
# [('Docker', 0, None), ('Installation', 1, 0), ('Usage', 2, 0), ('Kubernetes', 3, None)]

sections[sections[1].metadata.parent_id].section_header  # 'Docker'
```

The other relationships follow from these two fields:
- A section's children are the sections whose `parent_id` is its `id`.
- Sections with the same `parent_id` are siblings, whatever their header levels. In `# A`, `### C`, `## B`, both C and B are children of A. A skipped level adds no placeholder section.
- The previous and next sections in reading order have ids `id - 1` and `id + 1`.

Ids are unique within one document. To use them across documents, combine them with your own document key, such as `f"{doc_key}:{section.metadata.id}"`. Ids are positions, not content versions: inserting or removing a section renumbers the sections after it, and editing a section's text keeps its id. To detect changed sections between runs, for example to skip re-extracting entities from unchanged text, hash `section_text`. Changing `max_level` changes the tree and the ids.

### Breadcrumbs

`section.breadcrumb()` joins the parent headers and the section's own header. Sent with the section text, it tells an embedding model or LLM what the section is about when the text itself says "it" or "this step".
```python
text = "# Docker\n## Installation\nRun the installer."
section = splitter.split_text(text)[1]

section.breadcrumb()  # 'Docker > Installation'
section.breadcrumb(separator=" / ")  # 'Docker / Installation'

prompt_text = f"{section.breadcrumb()}\n\n{section.section_text}"
```

Text before the first header returns an empty string. The breadcrumb is computed from `metadata.parents`, so it is not part of the serialized section.

### Unicode normalization

With `normalize_unicode=True`, `split_text` and `split_file` transliterate each section's header and text to ASCII with [anyascii](https://github.com/anyascii/anyascii). The parents use the transliterated headers. It is off by default.
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
- An HTML comment or a `<pre>`, `<script>`, `<style>` or `<textarea>` block is only recognized when it starts the line. One that opens mid-line (`text <!--` or `text <pre>`) does not hide the `#` lines inside it.
- Headers inside `<details>` are split, as GitHub renders Markdown after a blank line inside `<details>`. The `<details>` and `</details>` tags stay in the text of the sections around them.
- A header with no text (`#`, `## ##`, or only whitespace after the `#`) is kept as text of the enclosing section, not an empty section. CommonMark renders it as an empty heading.
- A document that starts with `---` is treated as having YAML front matter only if the line after it is a `key:` entry and every line up to the next `---` or `...` looks like YAML (`key: value`, `- item`, indented lines, comments or blank lines). Otherwise the `---` is a horizontal rule and the headers after it are split as usual.

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

    # Join the parent headers and the section's header, such as "Docker > Installation"
    def breadcrumb(self, separator: str = " > ") -> str: ...
```

**SectionMetadata:** A Section's metadata: its id, its parent's id, its parent headers, whether Unicode normalization changed it, and where it is in the source text.
```python
class SectionMetadata(BaseModel):
    # Position in document order, starting at 0
    id: int | None
    # Id of the enclosing section, None for top-level sections
    parent_id: int | None
    # Whether Unicode normalization changed the header or text
    normalized: bool
    # Parent headers by level, such as {"h1": "Guide", "h2": "Install"}
    parents: dict[str, str]
    # Start (inclusive) and end (exclusive) offsets in the source text
    span: tuple[int, int]
    # Number of characters in the span, computed from it
    char_count: int
```

The span starts at the header line and ends at the last non-whitespace character of the section text. It does not include subsections, leading blank lines or trailing whitespace. Offsets count Python characters (code points), not UTF-8 bytes or UTF-16 units, in the string passed to `split_text`, including a byte order mark. `split_file` offsets index into the file's contents as decoded with its `encoding`, with line endings kept as written. A normalized section keeps the span and character count of the source text, so `text[start:end]` returns the text before transliteration.

### Methods

- `to_markdown()`: Convert to Markdown format
- `breadcrumb(separator=" > ")`: Join the parent headers and the section's own header

## Requirements
- Python 3.12+

## License
Apache License 2.0 - See [LICENSE](LICENSE)