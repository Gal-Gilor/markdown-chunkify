import logging
import time
from pathlib import Path

import pymupdf4llm

from markdown_chunkify.core.interfaces import BaseParser

logger = logging.getLogger(__name__)


class PyMuPDFMParser(BaseParser):
    """A wrapper around pymupdf4llm for parsing PDF files."""

    @classmethod
    def to_markdown(
        cls,
        file_path: str | Path,
        destination_path: str | Path | None = None,
        **kwargs,
    ) -> str:
        """Convert PDF file to markdown text.

        Args:
            file_path (str | Path): Path to the PDF file.
            destination_path (str | Path | None): A directory to save the Markdown file in.
                If provided, the Markdown is saved as `<PDF file name>.md` in that
                directory (for example, `docs/report.pdf` is saved as `report.md`).
                If the directory does not exist, it will be created.

        Returns:
            str: A Markdown representation of the PDF file.
        """
        path = Path(file_path)
        logger.info(f"Starting the PDF to Markdown conversion for: {path}")

        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        logger.debug(f"Converting PDF to Markdown: {path}")
        start_time = time.time()
        markdown = pymupdf4llm.to_markdown(file_path, **kwargs)
        logger.info(
            f"{path} was successfully converted to Markdown in "
            f"{time.time() - start_time:.2f} seconds."
        )

        if destination_path:
            destination = Path(destination_path)
            logger.debug(f"Preparing to save Markdown to: {destination}")
            destination.mkdir(parents=True, exist_ok=True)
            markdown_output_path = destination / f"{path.stem}.md"

            with open(markdown_output_path, "w", encoding="utf-8") as f:
                f.write(markdown)

            logger.info(
                f"{path} was successfully saved to: {markdown_output_path} as Markdown."
            )

        return markdown
