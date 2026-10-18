import pytest
from pydantic import ValidationError

from markdown_chunkify.components.splitters import MarkdownSplitter
from markdown_chunkify.core.models import SectionMetadata


def test_empty_input(splitter):
    """ "Test empty input for the MarkdownSplitter."""
    assert splitter.split_text("") == []
    assert splitter.split_text("   ") == []


def test_single_header(splitter):
    """Test a single header in a sample markdown text."""
    text = "# Header\nContent"
    sections = splitter.split_text(text)
    assert len(sections) == 1
    assert sections[0].section_header == "Header"
    assert sections[0].section_text == "Content"
    assert sections[0].header_level == 1


def test_multiple_headers_same_level(splitter):
    """Test multiple headers at the same level in a sample markdown text."""
    text = "# H1\nC1\n# H2\nC2"
    sections = splitter.split_text(text)
    assert len(sections) == 2
    assert [s.section_header for s in sections] == ["H1", "H2"]
    assert [s.section_text for s in sections] == ["C1", "C2"]


def test_nested_headers(splitter, nested_markdown):
    """Test nested headers in a sample markdown text."""
    sections = splitter.split_text(nested_markdown)
    assert len(sections) == 4
    assert [s.header_level for s in sections] == [1, 2, 3, 2]
    assert sections[2].metadata.parents["h1"] == "Main"
    assert sections[2].metadata.parents["h2"] == "Sub"


def test_parent_headers(splitter, sample_markdown):
    """Test parent headers in a sample markdown text."""
    sections = splitter.split_text(sample_markdown)
    assert sections[1].metadata.parents["h1"] == "Header 1"
    assert sections[-2].metadata.parents["h1"] == "Header 2"
    assert sections[-2].metadata.parents["h2"] == "Header 2.1"


def test_sibling_headers(splitter, sample_markdown):
    """Siblings share a parent_id, and their own children do not change that."""
    sections = splitter.split_text(sample_markdown)
    header_2 = sections[2]

    assert header_2.section_header == "Header 2"
    assert [s.section_header for s in sections if s.metadata.parent_id == 2] == [
        "Header 2.1",
        "Header 2.2",
    ]


def test_ids_are_document_order(splitter, sample_markdown):
    """Each id is the section's index, and each parent comes before its children."""
    sections = splitter.split_text(sample_markdown)

    assert [s.metadata.id for s in sections] == list(range(len(sections)))
    assert [s.metadata.parent_id for s in sections] == [None, 0, None, 2, 3, 2]
    for section in sections:
        if section.metadata.parent_id is not None:
            parent = sections[section.metadata.parent_id]
            assert parent.header_level < section.header_level
            assert section.metadata.parents[f"h{parent.header_level}"] == (
                parent.section_header
            )


def test_ids_do_not_depend_on_normalization(splitter):
    """Normalization changes the text, not the ids."""
    text = "Préface\n# Café\n## Straße\n# B"
    normalized = splitter.split_text(text, normalize_unicode=True)
    source = splitter.split_text(text)

    assert [(s.metadata.id, s.metadata.parent_id) for s in normalized] == [
        (s.metadata.id, s.metadata.parent_id) for s in source
    ]


def test_file_operations(splitter, tmp_path):
    # Create a temporary markdown file
    md_file = tmp_path / "test.md"
    md_file.write_text("# Test\nContent")

    sections = splitter.split_file(md_file)
    assert len(sections) == 1
    assert sections[0].section_header == "Test"


def test_file_not_found(splitter):
    """Test file not found error."""
    with pytest.raises(FileNotFoundError):
        splitter.split_file("nonexistent.md")


def test_is_directory(splitter, tmp_path):
    """Test if the path is a directory."""
    with pytest.raises(IsADirectoryError):
        splitter.split_file(tmp_path)


def test_header_level_counting(splitter):
    """Test header level counting in a sample markdown text."""
    text = "### Header"
    sections = splitter.split_text(text)
    assert sections[0].header_level == 3


def test_metadata_structure(splitter):
    """Test metadata structure in a sample markdown text."""
    text = "# H1\n## H2"
    sections = splitter.split_text(text)

    assert all(isinstance(section.metadata.parents, dict) for section in sections)
    assert sections[0].metadata.parents == {}
    assert "h1" in sections[1].metadata.parents


def test_to_markdown(splitter, sample_markdown):
    """Test to_markdown method in a sample markdown text."""
    sections = splitter.split_text(sample_markdown)
    assert sections[0].to_markdown() == "# Header 1\n\nContent 1"


def test_breadcrumb(splitter, nested_markdown):
    """The breadcrumb joins the parent headers and the section's own header."""
    sections = splitter.split_text(nested_markdown)

    assert [s.breadcrumb() for s in sections] == [
        "Main",
        "Main > Sub",
        "Main > Sub > Deep",
        "Main > Sub 2",
    ]
    assert sections[2].breadcrumb(separator=" / ") == "Main / Sub / Deep"


def test_breadcrumb_preamble_and_skipped_levels(splitter):
    """The preamble has an empty breadcrumb, and skipped levels add nothing."""
    sections = splitter.split_text("Intro\n# A\n### C")

    assert [s.breadcrumb() for s in sections] == ["", "A", "A > C"]


def test_breadcrumb_follows_normalization(splitter):
    """The breadcrumb uses the same headers as the section and its parents."""
    text = "# Café\n## Straße"

    assert splitter.split_text(text)[1].breadcrumb() == "Café > Straße"
    assert splitter.split_text(text, normalize_unicode=True)[1].breadcrumb() == (
        "Cafe > Strasse"
    )


def test_parents_reject_none():
    """A None parent header fails validation instead of breaking breadcrumb()."""
    with pytest.raises(ValidationError):
        SectionMetadata(parents={"h1": None}, span=(0, 0))


def test_char_count_is_derived_from_span():
    """char_count is computed from span, serialized, and cannot be set separately."""
    metadata = SectionMetadata(span=(2, 9))

    assert metadata.char_count == 7
    assert metadata.model_dump()["char_count"] == 7
    assert SectionMetadata.model_validate(metadata.model_dump()) == metadata
    assert SectionMetadata(span=(0, 10), char_count=3).char_count == 10


def test_code_block_kept_verbatim(splitter):
    """Code blocks keep their comments, language tag and line breaks."""
    code_block = "```python\n# A comment, not a header\nx = 1\n```"
    sections = splitter.split_text(f"# Header\n{code_block}\nAfter")

    assert len(sections) == 1
    assert sections[0].section_text == f"{code_block}\nAfter"


@pytest.mark.parametrize(
    "code_block",
    [
        "~~~\n# Not a header\n~~~",
        "````markdown\n```\n# Not a header\n```\n````",
        "```\n# Not a header\n````",
        "  ```\n# Not a header\n  ```",
    ],
)
def test_fence_variants(splitter, code_block):
    """Tilde, longer, and indented fences hide their content from header matching."""
    sections = splitter.split_text(f"# Header\n{code_block}\n# Next")

    assert [s.section_header for s in sections] == ["Header", "Next"]
    assert sections[0].section_text == code_block


def test_unclosed_fence_runs_to_end(splitter):
    """An unclosed fence hides the rest of the document from header matching."""
    sections = splitter.split_text("# Header\n```\n# Not a header\ntext")

    assert len(sections) == 1
    assert sections[0].section_text == "```\n# Not a header\ntext"


def test_header_levels_up_to_six(splitter):
    """Headers from h1 to h6 split, and parents only list levels that exist."""
    text = "\n".join(f"{'#' * level} H{level}" for level in range(1, 7))
    sections = splitter.split_text(text)

    assert [s.header_level for s in sections] == [1, 2, 3, 4, 5, 6]
    expected_parents = {f"h{level}": f"H{level}" for level in range(1, 6)}
    assert sections[-1].metadata.parents == expected_parents


def test_seven_hashes_is_text(splitter):
    """Seven or more '#' is not a header."""
    sections = splitter.split_text("# Header\n####### Not a header")

    assert len(sections) == 1
    assert sections[0].section_text == "####### Not a header"


def test_max_level(splitter):
    """Headers deeper than max_level stay in the enclosing section's text."""
    sections = MarkdownSplitter(max_level=2).split_text("# A\n## B\n### C\nText")

    assert [s.section_header for s in sections] == ["A", "B"]
    assert sections[1].section_text == "### C\nText"


@pytest.mark.parametrize("max_level", [0, 7])
def test_invalid_max_level(max_level):
    """max_level must be between 1 and 6."""
    with pytest.raises(ValueError):
        MarkdownSplitter(max_level=max_level)


def test_skipped_levels(splitter):
    """Skipped levels add no placeholder sections or parent keys.

    C and B are both children of A, so they are siblings although their levels differ,
    and each has its own child.
    """
    sections = splitter.split_text("# A\n### C\n#### E\n## B\n### D")

    assert [s.section_header for s in sections] == ["A", "C", "E", "B", "D"]
    assert [s.metadata.parent_id for s in sections] == [None, 0, 1, 0, 3]
    assert sections[1].metadata.parents == {"h1": "A"}
    assert sections[2].metadata.parents == {"h1": "A", "h3": "C"}


def test_mixed_levels_at_top_level(splitter):
    """Headers before any shallower header are top-level, whatever their level."""
    sections = splitter.split_text("## X\n# Y")

    assert [s.metadata.parent_id for s in sections] == [None, None]


def test_duplicate_headers_kept(splitter):
    """Headers with the same text under the same parent are separate sections."""
    sections = splitter.split_text("# A\n## Notes\nOne\n## Notes\nTwo")

    assert [(s.section_header, s.section_text) for s in sections[1:]] == [
        ("Notes", "One"),
        ("Notes", "Two"),
    ]
    assert [(s.metadata.id, s.metadata.parent_id) for s in sections[1:]] == [(1, 0), (2, 0)]


def test_duplicate_headers_in_outline(splitter):
    """The outline keeps headers with the same text as separate nodes."""
    outline = splitter.get_document_outline("# A\n## Notes\nOne\n## Notes\nTwo")

    assert [child.content for child in outline[0].children] == ["One", "Two"]


def test_siblings_do_not_leak_between_same_named_parents(splitter):
    """Children of different parents with the same text point to their own parent."""
    sections = splitter.split_text("# A\n## Setup\n### X\n# B\n## Setup\n### Y")
    by_header = {s.section_header: s for s in sections}

    assert by_header["X"].metadata.parent_id == 1
    assert by_header["Y"].metadata.parent_id == 4
    assert by_header["Y"].metadata.parents == {"h1": "B", "h2": "Setup"}


def test_preamble(splitter):
    """Text before the first header is a level-0 section with an empty header."""
    sections = splitter.split_text("Intro text\n\n# Header\nContent")

    assert sections[0].section_header == ""
    assert sections[0].header_level == 0
    assert sections[0].section_text == "Intro text"
    assert sections[0].to_markdown() == "Intro text"
    assert (sections[0].metadata.id, sections[0].metadata.parent_id) == (0, None)
    assert (sections[1].metadata.id, sections[1].metadata.parent_id) == (1, None)


def test_no_headers(splitter):
    """A document without headers is returned as one level-0 section."""
    sections = splitter.split_text("Just text.\nMore text.")

    assert len(sections) == 1
    assert sections[0].header_level == 0
    assert sections[0].section_text == "Just text.\nMore text."


@pytest.mark.parametrize(
    "line, expected_header",
    [
        ("## Title ##", "Title"),
        ("## #1 Priority", "#1 Priority"),
        ("   ## Indented", "Indented"),
        ("## C# Guide", "C# Guide"),
        ("# # #", "#"),
    ],
)
def test_header_text(splitter, line, expected_header):
    """Header text drops the closing '#' sequence and keeps '#' inside the text."""
    sections = splitter.split_text(line)

    assert sections[0].section_header == expected_header


@pytest.mark.parametrize(
    "line",
    ["#hashtag", "#", "    # Indented code", "#   \t", "# ", "## #", "# #", "## ##"],
)
def test_not_a_header(splitter, line):
    """Lines without a space after '#', bare '#' and 4-space indents are not headers.

    Empty headings (no text after the '#') are not headers either.
    """
    sections = splitter.split_text(f"# Header\n{line}\nNext line")

    assert len(sections) == 1
    assert sections[0].section_text == f"{line}\nNext line"


def test_windows_line_endings(splitter):
    """CRLF line endings do not end up in header text."""
    sections = splitter.split_text("# A\r\nText\r\n## B\r\nMore")

    assert [s.section_header for s in sections] == ["A", "B"]
    assert sections[0].section_text == "Text"


def test_no_text_lost(splitter, sample_markdown):
    """Every non-blank line of the input appears in the sections' Markdown."""
    text = f"Preamble\n{sample_markdown}\n## Header 2.2\nRepeated header"
    sections = splitter.split_text(text)
    output_lines = "\n".join(s.to_markdown() for s in sections).splitlines()

    assert [line for line in output_lines if line.strip()] == [
        line for line in text.splitlines() if line.strip()
    ]


def test_header_starting_with_hash(splitter):
    """A header whose text starts with '#' keeps it."""
    sections = splitter.split_text("## # Foo\nText")

    assert sections[0].section_header == "# Foo"


def test_front_matter_is_not_split(splitter):
    """'#' lines in YAML front matter are not headers; the front matter is the preamble."""
    front_matter = "---\ntitle: Guide\n# A YAML comment\n---"
    sections = splitter.split_text(f"{front_matter}\n# Real\nText")

    assert [s.section_header for s in sections] == ["", "Real"]
    assert sections[0].section_text == front_matter


def test_unclosed_front_matter_is_a_thematic_break(splitter):
    """A leading '---' without a closing line does not hide the headers after it."""
    sections = splitter.split_text("---\n# A\nText")

    assert [s.section_header for s in sections] == ["", "A"]


@pytest.mark.parametrize(
    "comment",
    ["<!--\n# Hidden\n-->", "<!-- note\n# Hidden -->", "<!-- one line -->"],
)
def test_html_comment_block(splitter, comment):
    """'#' lines inside an HTML comment block are not headers."""
    sections = splitter.split_text(f"# A\n{comment}\n# B")

    assert [s.section_header for s in sections] == ["A", "B"]
    assert sections[0].section_text == comment


@pytest.mark.parametrize(
    "block",
    [
        "<pre>\n# Hidden\n</pre>",
        "<script>\n# Hidden\n</script>",
        "<style>\n# Hidden\n</style>",
        "<textarea>\n# Hidden\n</textarea>",
        '<PRE class="x">\n# Hidden\n</PRE>',
        "<pre># a\n# b</pre>",
    ],
)
def test_raw_html_block(splitter, block):
    """'#' lines inside a <pre>, <script>, <style> or <textarea> block are not headers."""
    sections = splitter.split_text(f"# A\n{block}\n# B")

    assert [s.section_header for s in sections] == ["A", "B"]
    assert sections[0].section_text == block


@pytest.mark.parametrize("line", ["<pre>x</pre>", "<preview>"])
def test_line_that_does_not_open_raw_html_block(splitter, line):
    """A <pre> closed on its own line, or a tag like <preview>, hides no headers."""
    sections = splitter.split_text(f"# A\n{line}\n# B\n# C")

    assert [s.section_header for s in sections] == ["A", "B", "C"]


def test_details_headers_are_split(splitter):
    """Headers inside <details> are split.

    GitHub renders Markdown after a blank line inside <details> as Markdown, so the
    '# Inside' line is a heading there too.
    """
    details = "<details>\n<summary>More</summary>\n\n# Inside\n\n</details>"
    sections = splitter.split_text(f"# A\n{details}")

    assert [s.section_header for s in sections] == ["A", "Inside"]


@pytest.mark.parametrize(
    "list_item",
    [
        "- ```bash\n  # A comment\n  ```",
        "1. Install:\n   ```bash\n   # A comment\n   ```",
        "- Step\n    - ```bash\n      # A comment\n      ```",
    ],
)
def test_fence_in_list_item(splitter, list_item):
    """Fences on a list item line, or indented under one, hide their '#' lines."""
    sections = splitter.split_text(f"# A\n{list_item}\n# B")

    assert [s.section_header for s in sections] == ["A", "B"]
    assert sections[0].section_text == list_item


def test_setext_headers_are_text(splitter):
    """Setext headers are not supported and stay in the section text."""
    sections = splitter.split_text("# A\nTitle\n=====\nText")

    assert len(sections) == 1
    assert sections[0].section_text == "Title\n=====\nText"


def test_many_siblings():
    """Thousands of headers under one parent split, each pointing to the parent."""
    text = "# Root\n" + "\n".join(f"## H{index}\nText" for index in range(5000))
    sections = MarkdownSplitter().split_text(text)

    assert len(sections) == 5001
    assert all(s.metadata.parent_id == 0 for s in sections[1:])


def test_outline_ids(splitter):
    """Outline nodes carry the same ids and parent ids as the sections."""
    outline = splitter.get_document_outline("Intro\n# A\n## B\n# C")

    assert [(n.id, n.parent_id) for n in outline] == [(0, None), (1, None), (3, None)]
    assert (outline[1].children[0].id, outline[1].children[0].parent_id) == (2, 1)


def test_byte_order_mark_in_text(splitter):
    """A UTF-8 byte order mark before the first header does not hide it."""
    sections = splitter.split_text("\ufeff# Title\nText")

    assert [(s.header_level, s.section_header) for s in sections] == [(1, "Title")]


def test_byte_order_mark_in_outline(splitter):
    """get_document_outline also ignores a byte order mark."""
    outline = splitter.get_document_outline("\ufeff# Title\nText")

    assert [(node.level, node.header) for node in outline] == [(1, "Title")]


def test_byte_order_mark_in_file(splitter, tmp_path):
    """split_file reads a UTF-8 file with a byte order mark."""
    md_file = tmp_path / "bom.md"
    md_file.write_bytes("\ufeff# Title\nText".encode("utf-8"))

    sections = splitter.split_file(md_file)

    assert [(s.header_level, s.section_header) for s in sections] == [(1, "Title")]
    assert sections[0].section_text == "Text"


def test_split_file_spans_index_file_contents(splitter, tmp_path):
    """split_file spans index into the file's contents, BOM and CRLF included."""
    md_file = tmp_path / "crlf.md"
    contents = "\ufeffIntro\r\n# A\r\nalpha\r\n## B\r\nbeta\r\n"
    md_file.write_bytes(contents.encode("utf-8"))

    sections = splitter.split_file(md_file)

    assert [s.metadata for s in sections] == [
        s.metadata for s in splitter.split_text(contents)
    ]
    assert [contents[slice(*s.metadata.span)] for s in sections] == [
        "Intro",
        "# A\r\nalpha",
        "## B\r\nbeta",
    ]


def test_front_matter_with_lists_and_comments(splitter):
    """YAML front matter with lists, nested keys and comments is skipped."""
    front_matter = (
        "---\ntitle: Guide\ntags:\n  - one\n- two\n# A YAML comment\nauthor:\n"
        "  name: Gal\n\n..."
    )
    sections = splitter.split_text(f"{front_matter}\n# Real\nText")

    assert [s.section_header for s in sections] == ["", "Real"]
    assert sections[0].section_text == front_matter


def test_horizontal_rules_are_not_front_matter(splitter):
    """Two '---' lines around Markdown content are horizontal rules, not front matter."""
    sections = splitter.split_text("---\n# A\ntext\n---\n# B")

    assert [s.section_header for s in sections] == ["", "A", "B"]
    assert sections[1].section_text == "text\n---"


@pytest.mark.parametrize(
    "text, block, line_number",
    [
        ("# A\n    ```\n# B", "code fence", 2),
        ("# A\nText\n<!--\n# B", "HTML comment", 3),
        ("# A\n<pre>\n# B", "<pre> block", 2),
    ],
)
def test_unclosed_block_logs_warning(splitter, caplog, text, block, line_number):
    """An unclosed fence or HTML block logs a warning naming where it starts."""
    with caplog.at_level("WARNING", logger="markdown_chunkify"):
        sections = splitter.split_text(text)

    assert [s.section_header for s in sections] == ["A"]
    assert f"The {block} that starts on line {line_number} is never closed" in caplog.text


def test_closed_blocks_do_not_warn(splitter, caplog):
    """Closed fences and HTML comments do not log a warning."""
    with caplog.at_level("WARNING", logger="markdown_chunkify"):
        splitter.split_text("# A\n```\ncode\n```\n<!--\nnote\n-->\n# B")

    assert caplog.text == ""


def test_mid_line_html_comment_is_not_recognized(splitter):
    """A comment that opens mid-line does not hide the '#' lines inside it."""
    sections = splitter.split_text("# A\ntext <!--\n# B\n-->")

    assert [s.section_header for s in sections] == ["A", "B"]


@pytest.mark.parametrize(
    "text",
    ["---\n# Title\n---\n## Next", "---\n# Title\nAuthor: Gal\n---\n## Next"],
)
def test_front_matter_must_start_with_a_key(splitter, text):
    """A '---' block whose first line is not a 'key:' entry is not front matter."""
    sections = splitter.split_text(text)

    assert [(s.header_level, s.section_header) for s in sections] == [
        (0, ""),
        (1, "Title"),
        (2, "Next"),
    ]


def test_span_slices_section_from_source(splitter, sample_markdown):
    """Each span slices the header line and section text out of the source."""
    sections = splitter.split_text(sample_markdown)

    for section in sections:
        start, end = section.metadata.span
        assert sample_markdown[start:end].endswith(section.section_text)
        assert sample_markdown[start:end].lstrip().startswith("#")
        assert section.metadata.char_count == end - start


def test_span_offsets(splitter):
    """Spans skip leading blank lines and trailing whitespace, and exclude children."""
    text = "\n\nintro  \n\n# A\nText A\n## B   \n\n\n# C\n"
    sections = splitter.split_text(text)

    assert [s.metadata.span for s in sections] == [(2, 7), (11, 21), (22, 26), (32, 35)]
    assert [text[slice(*s.metadata.span)] for s in sections] == [
        "intro",
        "# A\nText A",
        "## B",
        "# C",
    ]
    assert [s.metadata.char_count for s in sections] == [5, 10, 4, 3]


def test_span_includes_byte_order_mark_offset(splitter):
    """Spans are offsets in the text as passed in, byte order mark included."""
    text = "﻿# Title\nText"
    sections = splitter.split_text(text)

    assert sections[0].metadata.span == (1, 13)
    assert text[1:13] == "# Title\nText"


def test_keeps_source_text_by_default(splitter):
    """By default, sections keep the source text, including entity names."""
    sections = splitter.split_text("# Müller GmbH\n北京")

    assert (sections[0].section_header, sections[0].section_text) == ("Müller GmbH", "北京")
    assert not sections[0].metadata.normalized


def test_normalize_unicode_enabled(splitter):
    """Headers, text and parents are transliterated to ASCII."""
    text = "# Café\nnaïve — “quoted”\n## Straße\nx\n## Ñu\ny"
    sections = splitter.split_text(text, normalize_unicode=True)

    assert [s.section_header for s in sections] == ["Cafe", "Strasse", "Nu"]
    assert sections[0].section_text == 'naive - "quoted"'
    assert sections[1].metadata.parents == {"h1": "Cafe"}


def test_normalize_unicode_disabled(splitter):
    """With normalize_unicode=False, sections keep the source text."""
    text = "# Café\nnaïve\n## Straße\nx"
    sections = splitter.split_text(text, normalize_unicode=False)

    assert [s.section_header for s in sections] == ["Café", "Straße"]
    assert sections[0].section_text == "naïve"
    assert sections[1].metadata.parents == {"h1": "Café"}
    assert not any(s.metadata.normalized for s in sections)
    start, end = sections[0].metadata.span
    assert text[start:end] == "# Café\nnaïve"


def test_normalized_spans_point_at_source(splitter):
    """Normalization keeps spans and character counts on the source text."""
    text = "Préface\n# Café\nStraße straße\n## B\nb"
    normalized = splitter.split_text(text, normalize_unicode=True)
    source = splitter.split_text(text)

    assert [s.metadata.span for s in normalized] == [s.metadata.span for s in source]
    assert [s.metadata.char_count for s in normalized] == [
        s.metadata.char_count for s in source
    ]
    assert normalized[0].section_text == "Preface"


def test_normalized_flag_marks_changed_sections(splitter):
    """Only sections whose header or text changed are marked as normalized."""
    text = "# Plain\ntext\n# Café\ntext\n# Plain 2\nnaïve"
    sections = splitter.split_text(text, normalize_unicode=True)

    assert [s.metadata.normalized for s in sections] == [False, True, True]


def test_fullwidth_hash_does_not_become_a_header(splitter):
    """Headers are found before normalization, so a fullwidth '＃' stays text."""
    sections = splitter.split_text("# Title\n＃ Not a header", normalize_unicode=True)

    assert [s.section_header for s in sections] == ["Title"]
    assert sections[0].section_text == "# Not a header"


def test_outline_keeps_source_text(splitter):
    """get_document_outline returns the source text, without normalization."""
    outline = splitter.get_document_outline("# Café\nnaïve")

    assert (outline[0].header, outline[0].content) == ("Café", "naïve")
    assert outline[0].model_dump() == {
        "header": "Café",
        "content": "naïve",
        "level": 1,
        "id": 0,
        "parent_id": None,
        "span": (0, 12),
        "children": [],
    }


def test_split_file_normalize_unicode(splitter, tmp_path):
    """split_file keeps the source text by default and passes normalize_unicode through."""
    md_file = tmp_path / "unicode.md"
    md_file.write_text("# Café\nnaïve", encoding="utf-8")

    normalized = splitter.split_file(md_file, normalize_unicode=True)
    source = splitter.split_file(md_file)

    assert (normalized[0].section_header, normalized[0].section_text) == ("Cafe", "naive")
    assert (source[0].section_header, source[0].section_text) == ("Café", "naïve")
