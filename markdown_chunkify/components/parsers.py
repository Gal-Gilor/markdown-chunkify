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
        file_name = Path(file_path)
        logger.info(f"Starting PDF the Markdown conversion for: {file_name}")

        if not Path(file_path).exists():
            error_msg = f"File not found: {file_path}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)

        try:
            logger.debug(f"Converting PDF to Markdown: {file_name}")
            start_time = time.time()
            markdown = pymupdf4llm.to_markdown(file_path, **kwargs)
            logger.info(
                f"{file_name} was successfully converted to Markdown in {time.time() - start_time:.2f} seconds."
            )

            if destination_path:
                logger.debug(f"Preparing to save Markdown to: {destination_path}")
                if isinstance(destination_path, str):
                    destination_path = Path(destination_path)

                try:
                    destination_path.mkdir(parents=True, exist_ok=True)
                    markdown_output_path = destination_path / f"{file_name}.md"

                    with open(markdown_output_path, "w", encoding="utf-8") as f:
                        f.write(markdown)

                    logger.info(
                        f"{file_name} was successfully saved to: {markdown_output_path} as Markdown."
                    )

                except Exception as e:
                    logger.error(
                        f"Failed to save the Markdown to: {destination_path}. Error: {str(e)}",
                        exc_info=True,
                    )
                    raise

            return markdown

        except Exception as e:
            logger.error(
                f"Failed to convert {file_name} to Markdown. Error: {str(e)}",
                exc_info=True,
            )
            raise
