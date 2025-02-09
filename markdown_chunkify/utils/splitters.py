import json
import re
from dataclasses import asdict
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from typing import Union


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


class MarkdownSplitter:
    """A class for splitting Markdown text by headers while maintaining hierarchy."""

    def __init__(self):
        # Regex to capture both the header level (number of #) and the header text
        self._header_pattern = re.compile(r"^(#+)\s+(.+)$", re.MULTILINE)

    def _get_header_level(self, header_marks: str) -> int:
        """Get the level of the header based on number of # marks."""
        return len(header_marks)

    def _find_parent_headers(
        self, current_level: int, header_stack: list[tuple[int, str]]
    ) -> dict[str, Optional[str]]:
        """Find parent headers for the current header level."""
        parents = {f"h{i}": None for i in range(1, 5)}  # Initialize all parent levels as None

        for level, header in header_stack:
            if (
                level < current_level
            ):  # Only headers of higher levels (fewer #) can be parents
                parents[f"h{level}"] = header

        return parents

    def split_markdown(self, text: str) -> list[MarkdownSection]:
        """Split Markdown text into sections while maintaining header hierarchy.

        The metadata includes the parent headers for each section up to 4 levels.

        Args:
            text (str): Markdown text to split.

        Returns:
            list[MarkdownSection]: List of markdown sections with hierarchy information.
        """
        if not text.strip():
            return []

        # Find all headers with their positions
        headers = list(self._header_pattern.finditer(text))
        sections = []
        header_stack: list[tuple[int, str]] = []  # Stack to track parent headers

        for i, match in enumerate(headers):
            # Get the current header's information
            header_marks = match.group(1)
            header_text = match.group(2).strip()
            current_level = self._get_header_level(header_marks)

            # Get the section text (everything between this header and the next)
            start_pos = match.end()
            end_pos = headers[i + 1].start() if i + 1 < len(headers) else len(text)
            section_text = text[start_pos:end_pos].strip()

            # Update header stack based on current header level
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

            # Remove missing parent headers metadata
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
            return splitter.split_markdown(f.read())
