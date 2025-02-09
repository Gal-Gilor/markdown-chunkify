import pytest

from markdown_chunkify.utils.splitters import MarkdownSplitter


def test_empty_input(splitter):
    assert splitter.split_markdown("") == []
    assert splitter.split_markdown("   ") == []


def test_single_header(splitter):
    text = "# Header\nContent"
    sections = splitter.split_markdown(text)
    assert len(sections) == 1
    assert sections[0].section_header == "Header"
    assert sections[0].section_text == "Content"
    assert sections[0].header_level == 1


def test_multiple_headers_same_level(splitter):
    text = "# H1\nC1\n# H2\nC2"
    sections = splitter.split_markdown(text)
    assert len(sections) == 2
    assert [s.section_header for s in sections] == ["H1", "H2"]
    assert [s.section_text for s in sections] == ["C1", "C2"]


def test_nested_headers(splitter, nested_markdown):
    sections = splitter.split_markdown(nested_markdown)
    assert len(sections) == 3
    assert [s.header_level for s in sections] == [1, 2, 3]
    assert sections[2].metadata["parents"]["h1"] == "Main"
    assert sections[2].metadata["parents"]["h2"] == "Sub"


def test_parent_headers(splitter, sample_markdown):
    sections = splitter.split_markdown(sample_markdown)
    assert sections[1].metadata["parents"]["h1"] == "Header 1"
    assert sections[-1].metadata["parents"]["h1"] == "Header 2"
    assert sections[-1].metadata["parents"]["h2"] == "Header 2.1"


def test_file_operations(tmp_path):
    # Create a temporary markdown file
    md_file = tmp_path / "test.md"
    md_file.write_text("# Test\nContent")

    sections = MarkdownSplitter.from_file(md_file)
    assert len(sections) == 1
    assert sections[0].section_header == "Test"


def test_file_not_found():
    with pytest.raises(FileNotFoundError):
        MarkdownSplitter.from_file("nonexistent.md")


def test_is_directory(tmp_path):
    with pytest.raises(IsADirectoryError):
        MarkdownSplitter.from_file(tmp_path)


def test_header_level_counting(splitter):
    text = "### Header"
    sections = splitter.split_markdown(text)
    assert sections[0].header_level == 3


def test_metadata_structure(splitter):
    text = "# H1\n## H2"
    sections = splitter.split_markdown(text)

    assert all("parents" in section.metadata for section in sections)
    assert all(isinstance(section.metadata["parents"], dict) for section in sections)
    assert sections[0].metadata["parents"] == {}
    assert "h1" in sections[1].metadata["parents"]


def test_to_dict(splitter, sample_markdown):
    sections = splitter.split_markdown(sample_markdown)
    assert sections[0].to_dict() == {
        "section_header": "Header 1",
        "section_text": "Content 1",
        "header_level": 1,
        "metadata": {"parents": {}},
    }


def test_to_markdown(splitter, sample_markdown):
    sections = splitter.split_markdown(sample_markdown)
    assert sections[0].to_markdown() == "# Header 1\n\nContent 1"
