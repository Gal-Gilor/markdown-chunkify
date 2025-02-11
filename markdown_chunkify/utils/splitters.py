import json
import os
import re
from dataclasses import asdict
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from typing import Union

from markdown_chunkify.core.models import BaseSplitter


@dataclass
class MarkdownSection:
    """Represents a section in a Markdown document with its header hierarchy."""

    section_header: str
    section_text: str
    header_level: int
    metadata: dict[str, dict[str, Optional[str]]]

    @classmethod
    def create(
        cls,
        header: str,
        text: str,
        header_level: int,
        parent_headers: dict[str, Optional[str]],
    ) -> "MarkdownSection":
        """Factory method to create a MarkdownSection with proper metadata structure."""
        return cls(
            section_header=header,
            section_text=text,
            header_level=header_level,
            metadata={"parents": parent_headers},
        )

    def to_dict(self) -> dict:
        """Convert the section to a dictionary for JSON serialization."""
        return asdict(self)

    def to_markdown(self) -> str:
        """Convert the section to a Markdown string."""
        return f"{'#' * self.header_level} {self.section_header}\n\n{self.section_text}"

    def __str__(self) -> str:
        """Return a pretty-printed JSON representation of the section."""
        return json.dumps(asdict(self), indent=2)


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
        parents = {f"h{i}": None for i in range(1, 5)}

        for level, header in header_stack:
            if level < current_level:  # Allow only H1 - H4 headers as parents
                parents[f"h{level}"] = header

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
            return []

        # Replace # wrapped in backticks with {{{{CODE_COMMENT}}}} tokens
        processed_text, replacement_map = self._process_code_blocks(text)

        # Find all headers with their positions
        headers = list(self._header_pattern.finditer(processed_text))
        sections = []
        header_stack: list[tuple[int, str]] = []

        for i, match in enumerate(headers):
            header_marks = match.group(1)
            header_text = match.group(2).strip()
            current_level = len(header_marks)

            # Extract section content (text between current header and next one)
            start_pos = match.end()
            end_pos = headers[i + 1].start() if i + 1 < len(headers) else len(processed_text)
            section_text = processed_text[start_pos:end_pos].strip()

            # Restore original code comments
            for token, original in replacement_map.items():
                section_text = section_text.replace(token, original)

            # Update header hierarchy
            while header_stack and header_stack[-1][0] >= current_level:
                header_stack.pop()
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

            sections.append(section)

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
            raise FileNotFoundError(f"Markdown file not found: {path}")

        if path.is_dir():
            raise IsADirectoryError(f"Path to Markdown file is a directory: {path}")

        splitter = cls()
        with path.open("r", encoding=encoding) as f:
            return splitter.split_text(f.read())
