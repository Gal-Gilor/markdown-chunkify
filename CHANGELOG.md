# Changelog

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2026-10-18

The first release on PyPI.

### Breaking changes

- Removed `UnicodeReplaceProcessor`, `BaseProcessor` and the `normalize` extra, which installed google-genai, jinja2 and tenacity. The metadata fields used only by the processor (`token_count`, `model_version`, `error` and `original_content`) are removed too. ([#15])
- Replaced `MarkdownSplitter.from_file` with the `split_file` function. Like `split_text`, it takes a keyword-only `max_level`. ([#15], [#37])
- Removed `metadata.siblings` and the `max_siblings` option. Sections with the same `parent_id` are siblings. ([#16])
- Added `metadata.id`, the section's position in document order starting at 0, and `metadata.parent_id`, the id of the enclosing section or `None`. Outline nodes from `get_document_outline` carry the same two fields. ([#16])
- Removed Unicode normalization and the anyascii dependency. `split_text` and `split_file` no longer take `normalize_unicode`, `metadata.normalized` is removed, and sections keep the source text. To get ASCII text, run `anyascii(section.content)` after splitting. ([#15], [#16], [#34])
- `metadata.parents` is typed `dict[str, str]` instead of `dict[str, str | None]`. ([#17])
- A header with no text (`#`, `## ##` or only whitespace after the `#`) stays as text of the enclosing section. Before, it became a section with `#` or whitespace as its header. ([#17])
- `get_document_outline` returns `OutlineNode` models instead of dicts. `OutlineNode` is exported from the package root, and `[node.model_dump() for node in outline]` returns the nodes as dicts. ([#24])
- Removed `PyMuPDFMParser`, `BaseParser` and the `pdf` extra, which installed pymupdf4llm. Call `pymupdf4llm.to_markdown()` directly to convert a PDF to Markdown. ([#33])
- Replaced `MarkdownSplitter` and `BaseSplitter` with the `split_text`, `split_file` and `get_document_outline` functions, which take a keyword-only `max_level`. Call `split_text(text, max_level=3)` instead of `MarkdownSplitter(max_level=3).split_text(text)`. The `markdown_chunkify.core` and `markdown_chunkify.components` modules are removed, so import from the package root. ([#37])
- Renamed `Section.section_header`, `section_text` and `header_level` to `header`, `content` and `level`, matching `OutlineNode`. ([#38])
- Removed `MarkdownContent`. Its fields are now part of `Section`. ([#38])
- `metadata.id` is a required `int` instead of `int | None`. ([#38])
- `Section`, `SectionMetadata` and `OutlineNode` are frozen, so their fields cannot be set after they're created. Call `section.model_copy(update={"content": "..."})` to get a changed copy. ([#38])

### Added

- `Section.breadcrumb(separator=" > ")` returns the parent headers and the section's own header, such as `Docker > Installation`. ([#16])
- A `py.typed` marker, so type checkers use the package's annotations.

### Changed

- Raised the minimum version to pydantic 2.14.1 and removed the upper bound. ([#15])

### Fixed

- `#` lines inside `<pre>`, `<script>`, `<style>` and `<textarea>` blocks are no longer split as headers. ([#17])

[0.3.0]: https://github.com/Gal-Gilor/markdown-chunkify/releases/tag/v0.3.0
[#15]: https://github.com/Gal-Gilor/markdown-chunkify/pull/15
[#16]: https://github.com/Gal-Gilor/markdown-chunkify/pull/16
[#17]: https://github.com/Gal-Gilor/markdown-chunkify/pull/17
[#24]: https://github.com/Gal-Gilor/markdown-chunkify/pull/24
[#33]: https://github.com/Gal-Gilor/markdown-chunkify/pull/33
[#34]: https://github.com/Gal-Gilor/markdown-chunkify/pull/34
[#37]: https://github.com/Gal-Gilor/markdown-chunkify/pull/37
[#38]: https://github.com/Gal-Gilor/markdown-chunkify/pull/38
