import os
import re
from pathlib import Path
from typing import Optional
from typing import Union

from markdown_chunkify.core.interfaces import BaseSplitter
from markdown_chunkify.core.models import MarkdownSection
from markdown_chunkify.core.settings import logger


class MarkdownSplitter(BaseSplitter):
    """A class for splitting Markdown text by headers while maintaining hierarchy."""

    def __init__(self):
        # Regex to capture both the header level (number of #) and the header text
        self._header_pattern = re.compile(r"^(#+)\s+(.+)$", re.MULTILINE)

    def _find_parent_headers(
        self, current_level: int, header_stack: list[tuple[int, str]]
    ) -> dict[str, Optional[str]]:
        """Find parent headers for the current header level."""
        # Initialize all parent levels as None
        logger.debug(f"Finding parents for header level: {current_level}.")
        parents = {f"h{i}": None for i in range(1, 5)}

        for level, header in header_stack:
            if level < current_level:  # Allow only H1 - H4 headers as parents
                parents[f"h{level}"] = header
                logger.debug(f"H{level} parent found: {header}.")

        return parents

    def _process_code_blocks(self, text: str) -> tuple[str, dict[str, str]]:
        """Identify Markdown code blocks and tokenize pound signs [#] in comments.

        Args:
            text: Raw Markdown text containing potential code blocks

        Returns:
            tuple: Contains:
                - str: Processed text with code comments replaced by tokens
                - dict: Mapping of tokens to their original comment text
        """
        logger.debug("Replacing code comments with tokens in code blocks")
        replacement_map = {}
        counter = 0

        def replace_comments(match):
            """Replace code comments with tokens in a single code block."""

            # Allows cpunter modification from the outer scope.
            nonlocal counter
            # Extract text between backticks
            code_block = match.group(1)
            lines = code_block.split("\n")
            processed_lines = []

            for line in lines:
                # Identify comments accounting for indentation
                if line.lstrip().startswith("#"):
                    token = f"{{{{CODE_COMMENT_{counter}}}}}"
                    replacement_map[token] = line
                    counter += 1
                    processed_lines.append(token)

                else:
                    processed_lines.append(line)

            logger.debug(f"Processed code block:\n{os.linesep.join(processed_lines)}.")

            return f"```{os.linesep.join(processed_lines)}```"

        # Process all code blocks in the text
        # Match content between triple backticks
        code_block_pattern = r"```(?:.*?)\n(.*?)```"
        processed_text = re.sub(code_block_pattern, replace_comments, text, flags=re.DOTALL)

        return processed_text, replacement_map

    def split_text(self, text: str) -> list[MarkdownSection]:
        """Split Markdown text into sections while maintaining header hierarchy.

        Args:
            text: Markdown text to split

        Returns:
            list[MarkdownSection]: List of markdown sections with hierarchy information
        """
        if not text.strip():
            logger.warning("`split_text` received empty text input.")
            return []

        # Replace # wrapped in backticks with {{{{CODE_COMMENT}}}} tokens
        logger.info("Splitting Markdown text by headers.")
        processed_text, replacement_map = self._process_code_blocks(text)

        # Find all headers with their positions
        headers = list(self._header_pattern.finditer(processed_text))
        logger.debug(f"Found {len(headers)} headers in the text.")

        header_stack: list[tuple[int, str]] = []
        sections = []
        for i, match in enumerate(headers):
            header_marks = match.group(1)
            header_text = match.group(2).strip()
            current_level = len(header_marks)

            logger.debug(f"Processing header: {header_text} at level {current_level}.")

            # Extract section content (text between current header and next one)
            start_pos = match.end()
            end_pos = headers[i + 1].start() if i + 1 < len(headers) else len(processed_text)
            section_text = processed_text[start_pos:end_pos].strip()

            # Restore original code comments
            for token, original in replacement_map.items():
                section_text = section_text.replace(token, original)

            # Update header hierarchy
            while header_stack and header_stack[-1][0] >= current_level:
                logger.debug(f"Removing header: {header_stack[-1][1]} from stack.")
                header_stack.pop()

            # Add current header to the stack
            header_stack.append((current_level, header_text))

            # Create section with parent information
            parent_headers = self._find_parent_headers(current_level, header_stack)
            section = MarkdownSection.create(
                header=header_text,
                text=section_text,
                header_level=current_level,
                parent_headers=parent_headers,
            )

            # Remove empty parent headers from metadata
            section.metadata["parents"] = {
                k: v for k, v in section.metadata["parents"].items() if v is not None
            }

            logger.debug(f"Created section: {section.section_header}.")
            metadata = section.metadata
            if metadata.get("parents"):
                logger.debug(
                    f"Section {section.section_header} parents: {metadata['parents']}."
                )

            sections.append(section)

        logger.info(f"Successfully split the Markdown into {len(sections)} sections.")

        return sections

    @classmethod
    def from_file(
        cls, filepath: Union[str, Path], encoding: str = "utf-8"
    ) -> list[MarkdownSection]:
        """Split Markdown text from a file by headers.

        Args:
            filepath (Union[str, Path]): Path to the Markdown file.

        Returns:
            list[MarkdownSection]: List of markdown sections with hierarchy information.

        Raises:
            FileNotFoundError: If the specified file does not exist.
            IsADirectoryError: If the specified path is a directory.
        """
        path = Path(filepath)
        if not path.exists():
            error_message = f"Unable to find the Markdown in the specified location: {path}"
            logger.error(error_message)
            raise FileNotFoundError(error_message)

        if path.is_dir():
            error_message = f"The provided path is a directory: {path}"
            logger.error(error_message)
            raise IsADirectoryError(error_message)

        try:
            splitter = cls()
            with path.open("r", encoding=encoding) as f:
                return splitter.split_text(f.read())

        except Exception as e:
            logger.error(
                f"Failed to split the Markdown file: {path}. Error: {str(e)}", exc_info=True
            )
            raise
