# Changelog

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2026-10-18

The first release on PyPI.

### Breaking changes

- Removed `UnicodeReplaceProcessor`, `BaseProcessor` and the `normalize` extra, which installed google-genai, jinja2 and tenacity. The metadata fields used only by the processor (`token_count`, `model_version`, `error` and `original_content`) are removed too. ([#15])
- Replaced `MarkdownSplitter.from_file` with the `split_file` method, which uses the splitter's `max_level`. ([#15], [#41])
- Removed `metadata.siblings` and the `max_siblings` option. Sections with the same `parent_id` are siblings. ([#16])
- Added `metadata.id`, the section's position in document order starting at 0, and `metadata.parent_id`, the id of the enclosing section or `None`. ([#16])
- Removed Unicode normalization and the anyascii dependency. `split_text` and `split_file` no longer take `normalize_unicode`, `metadata.normalized` is removed, and sections keep the source text. To get ASCII text, run `anyascii(section.content)` after splitting. ([#15], [#16], [#34])
- `metadata.parents` is typed `dict[str, str]` instead of `dict[str, str | None]`. ([#17])
- A header with no text (`#`, `## ##` or only whitespace after the `#`) stays as text of the enclosing section. Before, it became a section with `#` or whitespace as its header. ([#17])
- Removed `get_document_outline`. Build the tree from `metadata.parent_id`: a section's children are the sections whose `parent_id` is its `id`. ([#41])
- Removed `PyMuPDFMParser`, `BaseParser` and the `pdf` extra, which installed pymupdf4llm. Call `pymupdf4llm.to_markdown()` directly to convert a PDF to Markdown. ([#33])
- `MarkdownSplitter` takes `max_level` as a keyword-only argument and is immutable. Call `MarkdownSplitter(max_level=3)` instead of `MarkdownSplitter(3)`. ([#41])
- Removed `BaseSplitter` and the `markdown_chunkify.core` and `markdown_chunkify.components` modules. Import `MarkdownSplitter` and the models from the package root. ([#37])
- Renamed `Section.section_header`, `section_text` and `header_level` to `header`, `content` and `level`. ([#38])
- Removed `MarkdownContent`. Its fields are now part of `Section`. ([#38])
- `metadata.id` is a required `int` instead of `int | None`. ([#38])
- `Section` and `SectionMetadata` are frozen, so their fields cannot be set after they're created. Call `section.model_copy(update={"content": "..."})` to get a changed copy. ([#38])

### Added

- `Section.breadcrumb(separator=" > ")` returns the parent headers and the section's own header, such as `Docker > Installation`. ([#16])
- A `py.typed` marker, so type checkers use the package's annotations.

### Changed

- The minimum pydantic version is now 2.0.2, and the upper bound is removed. ([#15], [#40])

### Fixed

- `#` lines inside `<pre>`, `<script>`, `<style>` and `<textarea>` blocks are no longer split as headers. ([#17])
- `Section.to_markdown()` returns only the header line for a section without content, instead of the header followed by two newlines. ([#44])

[0.3.0]: https://github.com/Gal-Gilor/markdown-chunkify/releases/tag/v0.3.0
[#15]: https://github.com/Gal-Gilor/markdown-chunkify/pull/15
[#16]: https://github.com/Gal-Gilor/markdown-chunkify/pull/16
[#17]: https://github.com/Gal-Gilor/markdown-chunkify/pull/17
[#33]: https://github.com/Gal-Gilor/markdown-chunkify/pull/33
[#34]: https://github.com/Gal-Gilor/markdown-chunkify/pull/34
[#37]: https://github.com/Gal-Gilor/markdown-chunkify/pull/37
[#38]: https://github.com/Gal-Gilor/markdown-chunkify/pull/38
[#40]: https://github.com/Gal-Gilor/markdown-chunkify/pull/40
[#41]: https://github.com/Gal-Gilor/markdown-chunkify/pull/41
[#44]: https://github.com/Gal-Gilor/markdown-chunkify/pull/44
