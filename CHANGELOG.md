# Changelog

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2026-10-18

The first release on PyPI.

### Breaking changes

- Removed `UnicodeReplaceProcessor`, `BaseProcessor` and the `normalize` extra, which installed google-genai, jinja2 and tenacity. The metadata fields used only by the processor (`token_count`, `model_version`, `error` and `original_content`) are removed too. ([#15])
- Renamed `MarkdownSplitter.from_file` to `split_file`. It is an instance method like `split_text` and uses the splitter's `max_level` instead of taking it as an argument. ([#15])
- Removed `metadata.siblings` and the `max_siblings` option. Sections with the same `parent_id` are siblings. ([#16])
- Added `metadata.id`, the section's position in document order starting at 0, and `metadata.parent_id`, the id of the enclosing section or `None`. Outline nodes from `get_document_outline` carry the same two fields. ([#16])
- Unicode normalization is off by default. `split_text` and `split_file` keep the source text unless `normalize_unicode=True` is passed, which transliterates headers and text to ASCII with anyascii. anyascii is a new dependency. ([#15], [#16])
- `metadata.parents` is typed `dict[str, str]` instead of `dict[str, str | None]`. ([#17])
- A header with no text (`#`, `## ##` or only whitespace after the `#`) stays as text of the enclosing section. Before, it became a section with `#` or whitespace as its header. ([#17])

### Added

- `Section.breadcrumb(separator=" > ")` returns the parent headers and the section's own header, such as `Docker > Installation`. ([#16])
- A `py.typed` marker, so type checkers use the package's annotations.

### Changed

- Raised the minimum versions to pydantic 2.14.1 and pymupdf4llm 1.28.2 (`pdf` extra) and removed the upper bounds. ([#15])

### Fixed

- `#` lines inside `<pre>`, `<script>`, `<style>` and `<textarea>` blocks are no longer split as headers. ([#17])
- `PyMuPDFMParser.to_markdown` accepts a `Path` for `file_path` and `destination_path`, as `BaseParser` declares. ([#17])

[0.3.0]: https://github.com/Gal-Gilor/markdown-chunkify/releases/tag/v0.3.0
[#15]: https://github.com/Gal-Gilor/markdown-chunkify/pull/15
[#16]: https://github.com/Gal-Gilor/markdown-chunkify/pull/16
[#17]: https://github.com/Gal-Gilor/markdown-chunkify/pull/17
