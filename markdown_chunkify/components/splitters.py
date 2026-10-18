import logging
import re
from pathlib import Path
from typing import Dict
from typing import List
from typing import Optional
from typing import Union

from anyascii import anyascii

from markdown_chunkify.core.interfaces import BaseSplitter
from markdown_chunkify.core.models import Section
from markdown_chunkify.core.models import SectionMetadata

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
        - Optionally transliterates headers and text to ASCII ('Café' -> 'Cafe') with
          `normalize_unicode=True`, keeping spans on the source text

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
    def _front_matter_line_count(lines: List[str]) -> int:
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

    def _find_headers(self, text: str) -> List[tuple[int, int, int, str]]:
        """Find the headers outside fenced code blocks, HTML blocks and front matter.

        HTML blocks are HTML comments and <pre>, <script>, <style> and <textarea>
        blocks. An unclosed fence or HTML block runs to the end of the document, and a
        warning is logged because the headers after it are treated as text.

        Returns:
            List[tuple[int, int, int, str]]: For each header, the offset where its line
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

    def get_document_outline(self, text: str) -> List[Dict]:
        """Generate a nested document outline with the header hierarchy.

        Processes a Markdown document and creates a hierarchical structure that
        captures the relationships between headers and their content. Headers with the
        same text are kept as separate nodes.

        Args:
            text (str): The Markdown text to process. Should contain headers marked with '#'
                       (e.g., "# Header 1", "## Header 2", etc.).

        Returns:
            List[Dict]: The top-level nodes in document order. Each node contains:
                - header (str): The header text
                - content (str): The text under the header, up to the next header
                - level (int): The header level (1 for H1, 2 for H2, etc.)
                - children (List[Dict]): Nested headers under this header
                - id (int): The node's position in document order, starting at 0
                - parent_id (int | None): The id of the enclosing node. None for top-level
                  nodes
                - span (tuple[int, int]): The start and end offsets of the node's header
                  line and content in `text`, without leading blank lines and trailing
                  whitespace
                Text before the first header is the first node, with level 0 and an
                empty header.

        The header and content are the source text. Unicode normalization only applies
        to the sections returned by `split_text` and `split_file`.

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
                            "id": 1,
                            "parent_id": 0,
                            "span": (22, 46),
                        }
                    ],
                    "id": 0,
                    "parent_id": None,
                    "span": (1, 21),
                },
                {
                    "header": "Header 2",
                    "content": "Content 2",
                    "level": 1,
                    "children": [],
                    "id": 2,
                    "parent_id": None,
                    "span": (47, 67),
                },
            ]
        """
        return self._build_outline(text, normalize_unicode=False)

    @staticmethod
    def _normalize_node(node: Dict) -> None:
        """Transliterate a node's header and content to ASCII, recording if they changed."""
        header, content = anyascii(node["header"]), anyascii(node["content"])
        node["normalized"] = header != node["header"] or content != node["content"]
        node["header"], node["content"] = header, content

    def _build_outline(self, text: str, normalize_unicode: bool) -> List[Dict]:
        """Build the outline described in `get_document_outline`.

        With `normalize_unicode`, each node's header and content are transliterated to
        ASCII, so the parents of the sections match their headers. Spans stay offsets in
        the source text.
        """
        # Spans are offsets in the text as passed in, byte order mark included
        offset = len(_BYTE_ORDER_MARK) if text.startswith(_BYTE_ORDER_MARK) else 0
        text = text[offset:]
        if not text.strip():
            logger.warning("`get_document_outline` received empty text input.")
            return []

        headers = self._find_headers(text)
        document_outline = []
        # Nodes in document order. A node's index in this list is its id.
        nodes = []

        preamble_end = headers[0][0] if headers else len(text)
        preamble = self._trim(text[:preamble_end])
        if preamble:
            preamble_start = offset + text.index(preamble, 0, preamble_end)
            document_outline.append(
                {
                    "header": "",
                    "content": preamble,
                    "level": 0,
                    "children": [],
                    "id": 0,
                    "parent_id": None,
                    "span": (preamble_start, preamble_start + len(preamble)),
                }
            )
            nodes.append(document_outline[0])

        # Nodes on the path from the top level to the current header
        node_stack = []

        for i, (line_start, content_start, level, header_text) in enumerate(headers):
            content_end = headers[i + 1][0] if i + 1 < len(headers) else len(text)
            span_end = line_start + len(text[line_start:content_end].rstrip())

            while node_stack and node_stack[-1]["level"] >= level:
                node_stack.pop()

            node = {
                "header": header_text,
                "content": self._trim(text[content_start:content_end]),
                "level": level,
                "children": [],
                "id": len(nodes),
                "parent_id": node_stack[-1]["id"] if node_stack else None,
                "span": (offset + line_start, offset + span_end),
            }
            parent_children = node_stack[-1]["children"] if node_stack else document_outline
            parent_children.append(node)
            node_stack.append(node)
            nodes.append(node)

        if normalize_unicode:
            for node in nodes:
                self._normalize_node(node)

        return document_outline

    def _create_sections_from_outline(
        self, outline: List[Dict], parent_headers: Optional[Dict[str, str]] = None
    ) -> List[Section]:
        """Convert a document outline into a flat list of Section objects.

        Traverses the hierarchical document outline in document order and creates Section
        objects that keep the parent-child relationships.

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
                - metadata (SectionMetadata): Contains the section's id, its parent's id,
                  the parent headers, the section's span and its character count
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
                        id=node["id"],
                        parent_id=node["parent_id"],
                        parents=dict(parent_headers),
                        normalized=node.get("normalized", False),
                        span=node["span"],
                        char_count=node["span"][1] - node["span"][0],
                    ),
                )
            )

            child_parents = {**parent_headers, f"h{node['level']}": node["header"]}
            sections.extend(
                self._create_sections_from_outline(node["children"], child_parents)
            )

        return sections

    def split_text(self, text: str, normalize_unicode: bool = False) -> List[Section]:
        """Split Markdown text into sections while maintaining header hierarchy.

        Processes a Markdown document and splits it into sections based on
        headers. Each section records its id and its parent's id, so the hierarchy can be
        rebuilt: a section's children are the sections whose `parent_id` is its `id`, and
        sections with the same `parent_id` are siblings, whatever their header levels.
        Lines inside fenced code blocks are not treated as headers.

        Args:
            text (str): The Markdown text to split. Should contain headers marked with '#'
                       followed by a space (e.g., "# Header 1", "## Header 2").
            normalize_unicode (bool): Transliterate headers and text to ASCII with
                anyascii ('Café' -> 'Cafe', '—' -> '-'). This also rewrites non-Latin
                scripts ('Привет' -> 'Privet'), emoji, code and entity names ('Müller' ->
                'Muller'). Headers are found before the text is changed, so spans stay
                offsets in `text`. Defaults to False.

        Returns:
            List[Section]: A list of Section objects in document order, each containing:
                - section_header (str): The header text without '#' markers
                - section_text (str): The content between this header and the next
                - header_level (int): The level of the header (1 for H1, 2 for H2, etc.)
                - metadata (SectionMetadata): Contains:
                    - id (int): The section's index in the returned list
                    - parent_id (int | None): The id of the enclosing section, or None for
                      top-level sections
                    - parents (Dict[str, str]): Parent headers by level
                    - span (tuple[int, int]): The start and end offsets of the header line
                      and section text in `text`, so `text[start:end]` is the section as
                      written
                    - char_count (int): The number of characters in the span
                    - normalized (bool): Whether normalization changed the header or text
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
        if not text.removeprefix(_BYTE_ORDER_MARK).strip():
            logger.warning("`split_text` received empty text input.")
            return []

        outline = self._build_outline(text, normalize_unicode)
        sections = self._create_sections_from_outline(outline)

        logger.info(f"Successfully split the Markdown into {len(sections)} sections.")
        return sections

    def split_file(
        self,
        filepath: Union[str, Path],
        encoding: str = "utf-8-sig",
        normalize_unicode: bool = False,
    ) -> List[Section]:
        """Split a Markdown file into sections, as `split_text` does.

        Args:
            filepath (str | Path): The path to the Markdown file.
            encoding (str): The file encoding. The default, 'utf-8-sig', reads UTF-8
                files with or without a byte order mark.
            normalize_unicode (bool): Transliterate headers and text to ASCII. See
                `split_text`. Defaults to False.
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
            with path.open("r", encoding=encoding) as f:
                return self.split_text(f.read(), normalize_unicode=normalize_unicode)
        except Exception as e:
            logger.error(
                f"Failed to split the Markdown file: {path}. Error: {str(e)}", exc_info=True
            )
            raise
