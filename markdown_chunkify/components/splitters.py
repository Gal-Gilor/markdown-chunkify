import logging
import re
from pathlib import Path
from typing import Dict
from typing import List
from typing import Optional
from typing import Union

from markdown_chunkify.core.interfaces import BaseSplitter
from markdown_chunkify.core.models import Section
from markdown_chunkify.core.models import SectionMetadata

logger = logging.getLogger(__name__)

MAX_HEADER_LEVEL = 6

# ATX header: up to 3 spaces of indent, 1-6 '#', whitespace, the header text and an
# optional closing sequence of '#'.
_HEADER_PATTERN = re.compile(r"^ {0,3}(#{1,6})[ \t]+(.+?)(?:[ \t]+#+)?[ \t]*$")
# Opening code fence: 3+ backticks or tildes, at any indentation and optionally after a
# list marker, so fences inside list items are found. A backtick fence's info string
# cannot contain backticks.
_FENCE_OPEN_PATTERN = re.compile(
    r"^[ \t]*(?:(?:[-*+]|\d{1,9}[.)])[ \t]+)?(`{3,}(?!.*`)|~{3,})"
)
_FENCE_CLOSE_PATTERN = re.compile(r"^[ \t]*(`{3,}|~{3,})[ \t]*$")
# An HTML comment block starts with '<!--' at the start of a line and ends on the line
# that contains '-->'.
_HTML_COMMENT_OPEN_PATTERN = re.compile(r"^ {0,3}<!--")
_FRONT_MATTER_DELIMITERS = ("---", "...")
_LEADING_BLANK_LINES_PATTERN = re.compile(r"^\s*\n")


class MarkdownSplitter(BaseSplitter):
    """Split Markdown documents into sections based on header hierarchy.

    Processes Markdown documents and splits them into sections based on
    header levels (# through ######). It maintains the hierarchical relationships between
    sections and tracks sibling headers at the same level. Valid Markdown headers start
    with 1-6 '#' followed by a space (e.g., "# Header 1", "## Header 2").

    Key Features:
        - Splits Markdown text into sections based on headers
        - Maintains parent-child relationships between headers
        - Tracks sibling headers at the same level
        - Ignores lines inside fenced code blocks (``` or ~~~), HTML comment blocks and
          YAML front matter, so '#' lines there are not headers
        - Keeps section text exactly as written, including code blocks
        - Returns text before the first header as a level-0 section with an empty header
        - Supports headers up to level 6, or a lower limit set with `max_level`
        - Optionally caps each sibling list with `max_siblings`

    Limitations:
        - Only ATX headers ('#' to '######') are recognized. Setext headers, underlined
          with '===' or '---', are kept as text.
        - Headers and fences inside blockquotes ('> # Title') are not recognized.
        - A line indented by 4 or more spaces that starts with ``` or ~~~ is treated as a
          fence, even when it is part of an indented code block.
        - Without `max_siblings`, a section lists every other header at its level under
          the same parent. With n such headers, the sibling lists hold n * (n - 1) names,
          which gets slow for thousands of headers at one level.

    Example:
        >>> splitter = MarkdownSplitter()
        >>> text = '''
        ... # Introduction
        ... Markdown Splitting Made Easy.
        ... ## Installation
        ... To install the package, run the following command:
        ... ```bash
        ... # Install from source. Comment will not be treated as a header.
        ... pip install -e .
        ... ```
        ... ## Usage
        ... Basic usage examples...
        ... '''
        >>> sections = splitter.split_text(text)
        >>> for section in sections:
        ...     print(f"Header: {section.section_header}")
        ...     print(f"Level: {section.header_level}")
        ...     print(f"Parents: {section.metadata.parents}")
        ...     print(f"Siblings: {section.metadata.siblings}")
        Header: Introduction
        Level: 1
        Parents: {}
        Siblings: []
        Header: Installation
        Level: 2
        Parents: {'h1': 'Introduction'}
        Siblings: ['Usage']
        Header: Usage
        Level: 2
        Parents: {'h1': 'Introduction'}
        Siblings: ['Installation']
    """

    def __init__(self, max_level: int = MAX_HEADER_LEVEL, max_siblings: int | None = None):
        """Initialize the splitter.

        Args:
            max_level (int): The deepest header level to split on (1-6). Deeper headers
                are kept as text of the enclosing section.
            max_siblings (int | None): The maximum number of siblings listed per section.
                The siblings nearest to the section in document order are kept. None
                lists every sibling.
        """
        if not 1 <= max_level <= MAX_HEADER_LEVEL:
            raise ValueError(f"max_level must be between 1 and {MAX_HEADER_LEVEL}.")
        if max_siblings is not None and max_siblings < 0:
            raise ValueError("max_siblings must be 0 or greater.")
        self.max_level = max_level
        self.max_siblings = max_siblings

    @staticmethod
    def _closes_fence(line: str, fence: str) -> bool:
        """Check if a line closes a code fence opened with `fence`."""
        match = _FENCE_CLOSE_PATTERN.match(line)
        return bool(
            match and match.group(1)[0] == fence[0] and len(match.group(1)) >= len(fence)
        )

    @staticmethod
    def _front_matter_line_count(lines: List[str]) -> int:
        """Count the lines of YAML front matter at the start of the document.

        Front matter starts with a '---' line and ends with a '---' or '...' line. Without
        a closing line, the opening '---' is a thematic break and 0 is returned.
        """
        if not lines or lines[0].rstrip("\r") != _FRONT_MATTER_DELIMITERS[0]:
            return 0

        for index, line in enumerate(lines[1:], start=1):
            if line.rstrip("\r") in _FRONT_MATTER_DELIMITERS:
                return index + 1

        return 0

    def _find_headers(self, text: str) -> List[tuple[int, int, int, str]]:
        """Find the headers outside fenced code blocks, HTML comments and front matter.

        An unclosed fence or HTML comment runs to the end of the document.

        Returns:
            List[tuple[int, int, int, str]]: For each header, the offset where its line
                starts, the offset where its line ends, its level and its text.
        """
        headers = []
        fence = None
        in_html_comment = False
        position = 0
        lines = text.split("\n")
        front_matter_line_count = self._front_matter_line_count(lines)

        for index, line in enumerate(lines):
            line_start = position
            position += len(line) + 1
            line = line.rstrip("\r")

            if index < front_matter_line_count:
                continue

            if fence:
                if self._closes_fence(line, fence):
                    fence = None
                continue

            if in_html_comment:
                in_html_comment = "-->" not in line
                continue

            if _HTML_COMMENT_OPEN_PATTERN.match(line):
                in_html_comment = "-->" not in line[line.index("<!--") + 4 :]
                continue

            if fence_match := _FENCE_OPEN_PATTERN.match(line):
                fence = fence_match.group(1)
                continue

            header_match = _HEADER_PATTERN.match(line)
            if header_match and len(header_match.group(1)) <= self.max_level:
                level = len(header_match.group(1))
                headers.append((line_start, position, level, header_match.group(2)))

        return headers

    @staticmethod
    def _trim(text: str) -> str:
        """Remove leading blank lines and trailing whitespace, keeping indentation."""
        return _LEADING_BLANK_LINES_PATTERN.sub("", text).rstrip()

    def _nearest_siblings(self, names: List[str], index: int) -> List[str]:
        """Return the names around `index`, without it, capped at `max_siblings`."""
        if self.max_siblings is None or self.max_siblings >= len(names) - 1:
            return names[:index] + names[index + 1 :]

        # A window of max_siblings + 1 names that contains index, centered where possible.
        # With an odd max_siblings, the extra sibling comes from before the section.
        last_start = len(names) - 1 - self.max_siblings
        start = min(max(0, index - (self.max_siblings + 1) // 2), last_start)
        end = start + self.max_siblings + 1
        return names[start:index] + names[index + 1 : end]

    def _set_siblings(self, nodes: List[Dict]) -> None:
        """Set each node's siblings: other nodes at the same level under the same parent."""
        nodes_by_level = {}
        for node in nodes:
            nodes_by_level.setdefault(node["level"], []).append(node)

        for same_level_nodes in nodes_by_level.values():
            names = [node["header"] for node in same_level_nodes]
            for index, node in enumerate(same_level_nodes):
                node["siblings"] = self._nearest_siblings(names, index)

        for node in nodes:
            self._set_siblings(node["children"])

    def get_document_outline(self, text: str) -> List[Dict]:
        """Generate a nested document outline with header hierarchy and sibling relationships.

        Processes a Markdown document and creates a hierarchical structure that
        captures the relationships between headers, their content, and sibling headers at
        the same level. Headers with the same text are kept as separate nodes.

        Args:
            text (str): The Markdown text to process. Should contain headers marked with '#'
                       (e.g., "# Header 1", "## Header 2", etc.).

        Returns:
            List[Dict]: The top-level nodes in document order. Each node contains:
                - header (str): The header text
                - content (str): The text under the header, up to the next header
                - level (int): The header level (1 for H1, 2 for H2, etc.)
                - children (List[Dict]): Nested headers under this header
                - siblings (List[str]): Headers at the same level with the same parent
                Text before the first header is the first node, with level 0 and an
                empty header.

        Example:
            >>> text = '''
            ... # Header 1
            ... Content 1
            ... ## SubHeader A
            ... Content A
            ... # Header 2
            ... Content 2
            ... '''
            >>> MarkdownSplitter().get_document_outline(text)
            [
                {
                    "header": "Header 1",
                    "content": "Content 1",
                    "level": 1,
                    "children": [
                        {
                            "header": "SubHeader A",
                            "content": "Content A",
                            "level": 2,
                            "children": [],
                            "siblings": [],
                        }
                    ],
                    "siblings": ["Header 2"],
                },
                {
                    "header": "Header 2",
                    "content": "Content 2",
                    "level": 1,
                    "children": [],
                    "siblings": ["Header 1"],
                },
            ]
        """
        if not text.strip():
            logger.warning("`get_document_outline` received empty text input.")
            return []

        headers = self._find_headers(text)
        document_outline = []

        preamble = self._trim(text[: headers[0][0] if headers else len(text)])
        if preamble:
            document_outline.append(
                {
                    "header": "",
                    "content": preamble,
                    "level": 0,
                    "children": [],
                    "siblings": [],
                }
            )

        # Nodes on the path from the top level to the current header
        node_stack = []

        for i, (_, content_start, level, header_text) in enumerate(headers):
            content_end = headers[i + 1][0] if i + 1 < len(headers) else len(text)
            node = {
                "header": header_text,
                "content": self._trim(text[content_start:content_end]),
                "level": level,
                "children": [],
                "siblings": [],
            }

            while node_stack and node_stack[-1]["level"] >= level:
                node_stack.pop()

            parent_children = node_stack[-1]["children"] if node_stack else document_outline
            parent_children.append(node)
            node_stack.append(node)

        self._set_siblings(document_outline)

        return document_outline

    def _create_sections_from_outline(
        self, outline: List[Dict], parent_headers: Optional[Dict[str, str]] = None
    ) -> List[Section]:
        """Convert a document outline into a flat list of Section objects.

        Traverses the hierarchical document outline in document order and creates Section
        objects that keep the parent-child relationships and sibling connections.

        Args:
            outline (List[Dict]): Nodes as returned by `get_document_outline`.
            parent_headers (Dict[str, str], optional): A dictionary mapping the levels of the
                ancestor headers to their text. Keys are in the format 'h1', 'h2', etc.
                Defaults to None, which means the nodes have no ancestors.

        Returns:
            List[Section]: A flat list of Section objects, each containing:
                - section_header (str): The header text
                - section_text (str): The content under the header
                - header_level (int): The level of the header
                - metadata (SectionMetadata): Contains parent headers and sibling information
        """
        parent_headers = parent_headers or {}
        sections = []

        for node in outline:
            sections.append(
                Section(
                    section_header=node["header"],
                    section_text=node["content"],
                    header_level=node["level"],
                    metadata=SectionMetadata(
                        parents=dict(parent_headers), siblings=node["siblings"]
                    ),
                )
            )

            child_parents = {**parent_headers, f"h{node['level']}": node["header"]}
            sections.extend(
                self._create_sections_from_outline(node["children"], child_parents)
            )

        return sections

    def split_text(self, text: str) -> List[Section]:
        """Split Markdown text into sections while maintaining header hierarchy.

        Processes a Markdown document and splits it into sections based on
        headers. It maintains the hierarchical relationships between sections and tracks
        sibling headers at the same level. Sibling relationships are based on headers at
        the same level with the same parent. Lines inside fenced code blocks are not
        treated as headers.

        Args:
            text (str): The Markdown text to split. Should contain headers marked with '#'
                       followed by a space (e.g., "# Header 1", "## Header 2").

        Returns:
            List[Section]: A list of Section objects in document order, each containing:
                - section_header (str): The header text without '#' markers
                - section_text (str): The content between this header and the next
                - header_level (int): The level of the header (1 for H1, 2 for H2, etc.)
                - metadata (SectionMetadata): Contains:
                    - parents (Dict[str, str]): Parent headers by level
                    - siblings (List[str]): Other headers at same level with same parent
                Text before the first header, or a document without headers, is returned
                as a section with level 0 and an empty header.

        Example:
            >>> text = '''
            ... # Main Topic
            ... Introduction text
            ... ## Sub Topic A
            ... Content A
            ... ## Sub Topic B
            ... Content B
            ... '''
            >>> sections = splitter.split_text(text)
            >>> sections[0].section_header
            'Main Topic'
            >>> sections[1].metadata.parents
            {'h1': 'Main Topic'}
            >>> sections[1].metadata.siblings
            ['Sub Topic B']
        """
        if not text.strip():
            logger.warning("`split_text` received empty text input.")
            return []

        outline = self.get_document_outline(text)
        sections = self._create_sections_from_outline(outline)

        logger.info(f"Successfully split the Markdown into {len(sections)} sections.")
        return sections

    @classmethod
    def from_file(
        cls,
        filepath: Union[str, Path],
        encoding: str = "utf-8",
        max_level: int = MAX_HEADER_LEVEL,
        max_siblings: int | None = None,
    ) -> List[Section]:
        """Create sections from a Markdown file."""
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
            splitter = cls(max_level=max_level, max_siblings=max_siblings)
            with path.open("r", encoding=encoding) as f:
                return splitter.split_text(f.read())
        except Exception as e:
            logger.error(
                f"Failed to split the Markdown file: {path}. Error: {str(e)}", exc_info=True
            )
            raise
