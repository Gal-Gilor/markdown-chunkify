import logging
import re
from pathlib import Path

from markdown_chunkify.core.interfaces import BaseSplitter
from markdown_chunkify.models import OutlineNode
from markdown_chunkify.models import Section
from markdown_chunkify.models import SectionMetadata

logger = logging.getLogger(__name__)

MAX_HEADER_LEVEL = 6

# ATX header: up to 3 spaces of indent, 1-6 '#', then optionally whitespace and the
# header text, and an optional closing sequence of '#'. A header without text is not a
# header, so its line stays in the section text.
_HEADER_PATTERN = re.compile(r"^ {0,3}(#{1,6})(?:[ \t]+(.*?))??(?:[ \t]+#+)?[ \t]*$")
# Opening code fence: 3+ backticks or tildes, at any indentation and optionally after a
# list marker, so fences inside list items are found. A backtick fence's info string
# cannot contain backticks.
_FENCE_OPEN_PATTERN = re.compile(
    r"^[ \t]*(?:(?:[-*+]|\d{1,9}[.)])[ \t]+)?(`{3,}(?!.*`)|~{3,})"
)
_FENCE_CLOSE_PATTERN = re.compile(r"^[ \t]*(`{3,}|~{3,})[ \t]*$")
# An HTML comment block starts with '<!--' at the start of a line and ends on the line
# that contains '-->'. A <pre>, <script>, <style> or <textarea> block (CommonMark HTML
# block type 1) starts with its opening tag at the start of a line and ends on the line
# that contains its closing tag. Both are case-insensitive.
_HTML_BLOCK_OPEN_PATTERN = re.compile(
    r"^ {0,3}(?:<!--|<(pre|script|style|textarea)(?:[ \t>]|$))", re.IGNORECASE
)
_FRONT_MATTER_DELIMITERS = ("---", "...")
# A YAML 'key:' entry. The first line of front matter must be one.
_FRONT_MATTER_KEY_PATTERN = re.compile(r"^[\w\"'][^:]*:(?:[ \t]|$)")
# A line that can appear in YAML front matter: a 'key:' entry, a '- ' list item, an
# indented continuation, a YAML comment or a blank line.
_FRONT_MATTER_LINE_PATTERN = re.compile(
    r"^(?:[\w\"'][^:]*:(?:[ \t]|$)|-(?:[ \t]|$)|[ \t#]|$)"
)
_BYTE_ORDER_MARK = "\ufeff"
_LEADING_BLANK_LINES_PATTERN = re.compile(r"^\s*\n")


class MarkdownSplitter(BaseSplitter):
    """Split Markdown documents into sections based on header hierarchy.

    Processes Markdown documents and splits them into sections based on
    header levels (# through ######). Each section gets an id and the id of its parent
    section, so the header hierarchy can be rebuilt as a tree. Valid Markdown headers
    start with 1-6 '#' followed by a space (e.g., "# Header 1", "## Header 2").

    Key Features:
        - Splits Markdown text into sections based on headers
        - Gives each section an id (its position in document order) and its parent's id
        - Ignores lines inside fenced code blocks (``` or ~~~), HTML comment blocks,
          <pre>, <script>, <style> and <textarea> blocks and YAML front matter, so '#'
          lines there are not headers
        - Keeps section text exactly as written, including code blocks
        - Returns text before the first header as a level-0 section with an empty header
        - Supports headers up to level 6, or a lower limit set with `max_level`

    Limitations:
        - Only ATX headers ('#' to '######') are recognized. Setext headers, underlined
          with '===' or '---', are kept as text.
        - Headers and fences inside blockquotes ('> # Title') are not recognized.
        - A line indented by 4 or more spaces that starts with ``` or ~~~ is treated as a
          fence, even when it is part of an indented code block. If such a fence is never
          closed, the headers after it are treated as text and a warning is logged.
        - An HTML comment or a <pre>, <script>, <style> or <textarea> block is only
          recognized when it starts the line. One that opens mid-line ('text <!--' or
          'text <pre>') does not hide the '#' lines inside it.
        - Headers inside <details> are split, as GitHub renders Markdown after a blank
          line inside <details>. The <details> and </details> tags stay in the text of
          the sections around them.
        - A header with no text ('#', '## ##' or only whitespace after the '#') is kept as
          text of the enclosing section, not an empty section.

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
        ...     print(f"Id: {section.metadata.id}")
        ...     print(f"Parent id: {section.metadata.parent_id}")
        ...     print(f"Parents: {section.metadata.parents}")
        Header: Introduction
        Level: 1
        Id: 0
        Parent id: None
        Parents: {}
        Header: Installation
        Level: 2
        Id: 1
        Parent id: 0
        Parents: {'h1': 'Introduction'}
        Header: Usage
        Level: 2
        Id: 2
        Parent id: 0
        Parents: {'h1': 'Introduction'}
    """

    def __init__(self, max_level: int = MAX_HEADER_LEVEL):
        """Initialize the splitter.

        Args:
            max_level (int): The deepest header level to split on (1-6). Deeper headers
                are kept as text of the enclosing section.
        """
        if not 1 <= max_level <= MAX_HEADER_LEVEL:
            raise ValueError(f"max_level must be between 1 and {MAX_HEADER_LEVEL}.")
        self.max_level = max_level

    @staticmethod
    def _closes_fence(line: str, fence: str) -> bool:
        """Check if a line closes a code fence opened with `fence`."""
        match = _FENCE_CLOSE_PATTERN.match(line)
        return bool(
            match and match.group(1)[0] == fence[0] and len(match.group(1)) >= len(fence)
        )

    @staticmethod
    def _front_matter_line_count(lines: list[str]) -> int:
        """Count the lines of YAML front matter at the start of the document.

        Front matter starts with a '---' line followed by a 'key:' line, ends with a '---'
        or '...' line, and every line between them looks like YAML. Otherwise the
        opening '---' is a thematic break and 0 is returned.
        """
        if len(lines) < 2 or lines[0].rstrip("\r") != _FRONT_MATTER_DELIMITERS[0]:
            return 0

        if not _FRONT_MATTER_KEY_PATTERN.match(lines[1].rstrip("\r")):
            return 0

        for index, line in enumerate(lines[1:], start=1):
            line = line.rstrip("\r")
            if line in _FRONT_MATTER_DELIMITERS:
                return index + 1
            if not _FRONT_MATTER_LINE_PATTERN.match(line):
                return 0

        return 0

    def _find_headers(self, text: str) -> list[tuple[int, int, int, str]]:
        """Find the headers outside fenced code blocks, HTML blocks and front matter.

        HTML blocks are HTML comments and <pre>, <script>, <style> and <textarea>
        blocks. An unclosed fence or HTML block runs to the end of the document, and a
        warning is logged because the headers after it are treated as text.

        Returns:
            list[tuple[int, int, int, str]]: For each header, the offset where its line
                starts, the offset where its line ends, its level and its text.
        """
        headers = []
        fence = None
        # The text that ends the open HTML block: '-->' or a closing tag such as '</pre>'
        html_block_end = None
        # 1-based line number where the open fence or HTML block started
        block_start_line = 0
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

            if html_block_end:
                if html_block_end in line.lower():
                    html_block_end = None
                continue

            if html_match := _HTML_BLOCK_OPEN_PATTERN.match(line):
                tag = html_match.group(1)
                block_end = f"</{tag.lower()}>" if tag else "-->"
                if block_end not in line[html_match.end() :].lower():
                    html_block_end = block_end
                block_start_line = index + 1
                continue

            if fence_match := _FENCE_OPEN_PATTERN.match(line):
                fence = fence_match.group(1)
                block_start_line = index + 1
                continue

            header_match = _HEADER_PATTERN.match(line)
            if (
                header_match
                and header_match.group(2)
                and len(header_match.group(1)) <= self.max_level
            ):
                level = len(header_match.group(1))
                headers.append((line_start, position, level, header_match.group(2)))

        if fence or html_block_end:
            if fence:
                block = "code fence"
            elif html_block_end == "-->":
                block = "HTML comment"
            else:
                block = f"<{html_block_end[2:-1]}> block"
            logger.warning(
                f"The {block} that starts on line {block_start_line} is never closed. "
                "Headers after it are treated as text."
            )

        return headers

    @staticmethod
    def _trim(text: str) -> str:
        """Remove leading blank lines and trailing whitespace, keeping indentation."""
        return _LEADING_BLANK_LINES_PATTERN.sub("", text).rstrip()

    def get_document_outline(self, text: str) -> list[OutlineNode]:
        """Generate a nested document outline with the header hierarchy.

        Processes a Markdown document and creates a hierarchical structure that
        captures the relationships between headers and their content. Headers with the
        same text are kept as separate nodes.

        Args:
            text (str): The Markdown text to process. Should contain headers marked with '#'
                       (e.g., "# Header 1", "## Header 2", etc.).

        Returns:
            list[OutlineNode]: The top-level nodes in document order. Each node holds a
                header and its content, level, id, parent id and span, and the nodes of
                the headers nested under it in `children`. Text before the first header
                is the first node, with level 0 and an empty header.

        Example:
            >>> text = '''
            ... # Header 1
            ... Content 1
            ... ## SubHeader A
            ... Content A
            ... # Header 2
            ... Content 2
            ... '''
            >>> outline = MarkdownSplitter().get_document_outline(text)
            >>> [(node.header, node.id) for node in outline]
            [('Header 1', 0), ('Header 2', 2)]
            >>> child = outline[0].children[0]
            >>> child.header, child.content, child.parent_id, child.span
            ('SubHeader A', 'Content A', 0, (22, 46))
        """
        # Spans are offsets in the text as passed in, byte order mark included
        offset = len(_BYTE_ORDER_MARK) if text.startswith(_BYTE_ORDER_MARK) else 0
        text = text[offset:]
        if not text.strip():
            return []

        headers = self._find_headers(text)
        document_outline = []

        preamble_end = headers[0][0] if headers else len(text)
        preamble = self._trim(text[:preamble_end])
        if preamble:
            preamble_start = offset + text.index(preamble, 0, preamble_end)
            document_outline.append(
                OutlineNode(
                    header="",
                    content=preamble,
                    level=0,
                    id=0,
                    parent_id=None,
                    span=(preamble_start, preamble_start + len(preamble)),
                )
            )

        # Ids are in document order, so the headers follow the preamble's id
        first_id = len(document_outline)
        # Nodes on the path from the top level to the current header
        node_stack = []

        for i, (line_start, content_start, level, header_text) in enumerate(headers):
            content_end = headers[i + 1][0] if i + 1 < len(headers) else len(text)
            span_end = line_start + len(text[line_start:content_end].rstrip())

            while node_stack and node_stack[-1].level >= level:
                node_stack.pop()

            node = OutlineNode(
                header=header_text,
                content=self._trim(text[content_start:content_end]),
                level=level,
                id=first_id + i,
                parent_id=node_stack[-1].id if node_stack else None,
                span=(offset + line_start, offset + span_end),
            )
            parent_children = node_stack[-1].children if node_stack else document_outline
            parent_children.append(node)
            node_stack.append(node)

        return document_outline

    def _create_sections_from_outline(
        self,
        outline: list[OutlineNode],
        parent_headers: dict[str, str] | None = None,
    ) -> list[Section]:
        """Convert a document outline into a flat list of Section objects.

        Traverses the hierarchical document outline in document order and creates Section
        objects that keep the parent-child relationships.

        Args:
            outline (list[OutlineNode]): Nodes as returned by `get_document_outline`.
            parent_headers (dict[str, str] | None): A dictionary mapping the levels of the
                ancestor headers to their text. Keys are in the format 'h1', 'h2', etc.
                Defaults to None, which means the nodes have no ancestors.

        Returns:
            list[Section]: A flat list of Section objects, each containing:
                - section_header (str): The header text
                - section_text (str): The content under the header
                - header_level (int): The level of the header
                - metadata (SectionMetadata): Contains the section's id, its parent's id,
                  the parent headers, the section's span and its character count
        """
        parent_headers = parent_headers or {}
        sections = []

        for node in outline:
            sections.append(
                Section(
                    section_header=node.header,
                    section_text=node.content,
                    header_level=node.level,
                    metadata=SectionMetadata(
                        id=node.id,
                        parent_id=node.parent_id,
                        parents=dict(parent_headers),
                        span=node.span,
                    ),
                )
            )

            child_parents = {**parent_headers, f"h{node.level}": node.header}
            sections.extend(self._create_sections_from_outline(node.children, child_parents))

        return sections

    def split_text(self, text: str) -> list[Section]:
        """Split Markdown text into sections while maintaining header hierarchy.

        Processes a Markdown document and splits it into sections based on
        headers. Each section records its id and its parent's id, so the hierarchy can be
        rebuilt: a section's children are the sections whose `parent_id` is its `id`, and
        sections with the same `parent_id` are siblings, whatever their header levels.
        Lines inside fenced code blocks are not treated as headers.

        Args:
            text (str): The Markdown text to split. Should contain headers marked with '#'
                       followed by a space (e.g., "# Header 1", "## Header 2").

        Returns:
            list[Section]: A list of Section objects in document order, each containing:
                - section_header (str): The header text without '#' markers
                - section_text (str): The content between this header and the next
                - header_level (int): The level of the header (1 for H1, 2 for H2, etc.)
                - metadata (SectionMetadata): Contains:
                    - id (int): The section's index in the returned list
                    - parent_id (int | None): The id of the enclosing section, or None for
                      top-level sections
                    - parents (dict[str, str]): Parent headers by level
                    - span (tuple[int, int]): The start and end offsets of the header line
                      and section text in `text`, so `text[start:end]` is the section as
                      written
                    - char_count (int): The number of characters in the span, computed
                      from it
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
            >>> sections[2].metadata.parent_id
            0
        """
        outline = self.get_document_outline(text)
        return self._create_sections_from_outline(outline)

    def split_file(self, filepath: str | Path, encoding: str = "utf-8") -> list[Section]:
        """Split a Markdown file into sections, as `split_text` does.

        Spans are character offsets into the file's contents as decoded with
        `encoding`, with line endings kept as written.

        Args:
            filepath (str | Path): The path to the Markdown file.
            encoding (str): The file encoding. The default, 'utf-8', keeps a byte
                order mark in the text, and spans count it. Passing 'utf-8-sig'
                removes it before splitting, so offsets start after it.
        """
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(
                f"Unable to find the Markdown in the specified location: {path}"
            )

        if path.is_dir():
            raise IsADirectoryError(f"The provided path is a directory: {path}")

        with path.open("r", encoding=encoding, newline="") as f:
            return self.split_text(f.read())
