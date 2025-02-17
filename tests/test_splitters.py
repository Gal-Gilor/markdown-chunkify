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
    assert len(sections) == 3
    assert [s.header_level for s in sections] == [1, 2, 3]
    assert sections[2].metadata.parents["h1"] == "Main"
    assert sections[2].metadata.parents["h2"] == "Sub"


def test_parent_headers(splitter, sample_markdown):
    """Test parent headers in a sample markdown text."""
    sections = splitter.split_text(sample_markdown)
    assert sections[1].metadata.parents["h1"] == "Header 1"
    assert sections[-1].metadata.parents["h1"] == "Header 2"
    assert sections[-1].metadata.parents["h2"] == "Header 2.1"


def test_number_of_sections(splitter, sample_markdown):
    """Test the number of sections in a sample markdown text."""
    sections = splitter.split_text(sample_markdown)
    assert len(sections) == 5


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
