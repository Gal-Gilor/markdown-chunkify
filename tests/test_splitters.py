import pytest

from markdown_chunkify.components.splitters import MarkdownSplitter


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
    """Test sibling headers in a sample markdown text."""
    sections = splitter.split_text(sample_markdown)
    assert sections[-3].metadata.siblings == ["Header 2.2"]
    assert sections[-1].metadata.siblings == ["Header 2.1"]


def test_file_operations(tmp_path):
    # Create a temporary markdown file
    md_file = tmp_path / "test.md"
    md_file.write_text("# Test\nContent")

    sections = MarkdownSplitter.from_file(md_file)
    assert len(sections) == 1
    assert sections[0].section_header == "Test"


def test_file_not_found():
    """Test file not found error."""
    with pytest.raises(FileNotFoundError):
        MarkdownSplitter.from_file("nonexistent.md")


def test_is_directory(tmp_path):
    """Test if the path is a directory."""
    with pytest.raises(IsADirectoryError):
        MarkdownSplitter.from_file(tmp_path)


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
    """A skipped level does not create a parent key for the missing level."""
    sections = splitter.split_text("# A\n### C\n## B")

    assert sections[1].metadata.parents == {"h1": "A"}
    assert sections[1].metadata.siblings == []
    assert sections[2].metadata.siblings == []


def test_duplicate_headers_kept(splitter):
    """Headers with the same text under the same parent are separate sections."""
    sections = splitter.split_text("# A\n## Notes\nOne\n## Notes\nTwo")

    assert [(s.section_header, s.section_text) for s in sections[1:]] == [
        ("Notes", "One"),
        ("Notes", "Two"),
    ]
    assert sections[1].metadata.siblings == ["Notes"]
    assert sections[2].metadata.siblings == ["Notes"]


def test_duplicate_headers_in_outline(splitter):
    """The outline keeps headers with the same text as separate nodes."""
    outline = splitter.get_document_outline("# A\n## Notes\nOne\n## Notes\nTwo")

    assert [child["content"] for child in outline[0]["children"]] == ["One", "Two"]


def test_siblings_do_not_leak_between_same_named_parents(splitter):
    """Children of different parents with the same text are not siblings."""
    sections = splitter.split_text("# A\n## Setup\n### X\n# B\n## Setup\n### Y")
    by_header = {s.section_header: s for s in sections}

    assert by_header["X"].metadata.siblings == []
    assert by_header["Y"].metadata.siblings == []
    assert by_header["Y"].metadata.parents == {"h1": "B", "h2": "Setup"}


def test_preamble(splitter):
    """Text before the first header is a level-0 section with an empty header."""
    sections = splitter.split_text("Intro text\n\n# Header\nContent")

    assert sections[0].section_header == ""
    assert sections[0].header_level == 0
    assert sections[0].section_text == "Intro text"
    assert sections[0].to_markdown() == "Intro text"
    assert sections[1].metadata.siblings == []


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
    ],
)
def test_header_text(splitter, line, expected_header):
    """Header text drops the closing '#' sequence and keeps '#' inside the text."""
    sections = splitter.split_text(line)

    assert sections[0].section_header == expected_header


@pytest.mark.parametrize("line", ["#hashtag", "#", "    # Indented code"])
def test_not_a_header(splitter, line):
    """Lines without a space after '#', bare '#' and 4-space indents are not headers."""
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


def test_max_siblings_keeps_nearest():
    """max_siblings keeps the siblings nearest to the section, in document order."""
    text = "\n".join(f"## H{index}" for index in range(6))
    sections = MarkdownSplitter(max_siblings=2).split_text(text)

    assert sections[0].metadata.siblings == ["H1", "H2"]
    assert sections[3].metadata.siblings == ["H2", "H4"]
    assert sections[5].metadata.siblings == ["H3", "H4"]


def test_max_siblings_zero():
    """max_siblings=0 lists no siblings."""
    sections = MarkdownSplitter(max_siblings=0).split_text("## A\n## B")

    assert [s.metadata.siblings for s in sections] == [[], []]


def test_invalid_max_siblings():
    """max_siblings cannot be negative."""
    with pytest.raises(ValueError):
        MarkdownSplitter(max_siblings=-1)


def test_max_siblings_bounds_large_documents():
    """With max_siblings, many headers at one level get short sibling lists."""
    text = "\n".join(f"## H{index}\nText" for index in range(5000))
    sections = MarkdownSplitter(max_siblings=4).split_text(text)

    assert len(sections) == 5000
    assert max(len(s.metadata.siblings) for s in sections) == 4


def test_from_file_max_siblings(tmp_path):
    """from_file passes max_siblings to the splitter."""
    md_file = tmp_path / "test.md"
    md_file.write_text("## A\n## B\n## C")

    sections = MarkdownSplitter.from_file(md_file, max_siblings=1)

    assert [s.metadata.siblings for s in sections] == [["B"], ["A"], ["B"]]
