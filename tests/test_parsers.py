import pytest

pytest.importorskip("pymupdf4llm")

from markdown_chunkify.components import parsers  # noqa: E402


@pytest.fixture(autouse=True)
def fake_conversion(monkeypatch):
    """Skip the real PDF conversion; the tests only cover where the file is saved."""
    monkeypatch.setattr(parsers.pymupdf4llm, "to_markdown", lambda *_, **__: "# Title")


def test_relative_pdf_path_saves_in_destination(tmp_path, monkeypatch):
    """A PDF in a subdirectory is saved as <stem>.md directly in the destination."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "report.pdf").write_bytes(b"")

    parsers.PyMuPDFMParser.to_markdown("docs/report.pdf", destination_path="out")

    assert (tmp_path / "out" / "report.md").read_text() == "# Title"


def test_absolute_pdf_path_saves_in_destination(tmp_path):
    """An absolute PDF path does not override the destination."""
    pdf_path = tmp_path / "pdfs" / "report.pdf"
    pdf_path.parent.mkdir()
    pdf_path.write_bytes(b"")
    destination = tmp_path / "out"

    parsers.PyMuPDFMParser.to_markdown(str(pdf_path), destination_path=str(destination))

    assert (destination / "report.md").read_text() == "# Title"
    assert not (tmp_path / "pdfs" / "report.pdf.md").exists()
