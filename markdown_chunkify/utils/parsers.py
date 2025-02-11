from pathlib import Path

import pymupdf4llm

from markdown_chunkify.core.models import BaseParser


class PyMuPDFMParser(BaseParser):
    """A wrapper around pymupdf4llm for parsing PDF files."""

    @classmethod
    def to_markdown(
        self, file_path: str, destination_path: str | None = None, **kwargs
    ) -> str:
        """Convert PDF file to markdown text.

        Args:
            file_path (str): Path to the PDF file.
            destination_path (str | None): Path to save the markdown file.
                If a path is provided, the markdown file will be saved to that location.
                If the directory does not exist, it will be created.

        Returns:
            str: A Markdown representation of the PDF file.
        """
        markdown = pymupdf4llm.to_markdown(file_path, **kwargs)

        # Create the destination path if it doesn't exist
        if destination_path:
            if isinstance(destination_path, str):
                destination_path = Path(destination_path)

            destination_path.mkdir(parents=True, exist_ok=True)
            file_name = Path(file_path).stem
            markdown_output_path = destination_path / f"{file_name}.md"

            # Save the markdown to the specified destination path
            with open(markdown_output_path, "w", encoding="utf-8") as f:
                f.write(markdown)

        return markdown
