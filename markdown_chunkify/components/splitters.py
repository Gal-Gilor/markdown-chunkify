import os
import re
from pathlib import Path
from typing import Dict
from typing import List
from typing import Optional
from typing import Union

from markdown_chunkify.core.interfaces import BaseSplitter
from markdown_chunkify.core.models import Section
from markdown_chunkify.core.models import SectionMetadata
from markdown_chunkify.core.settings import logger


class MarkdownSplitter(BaseSplitter):
    """Split Markdown documents into sections based on header hierarchy.

    Processes Markdown documents and splits them into sections based on
    header levels (# through #####). It maintains the hierarchical relationships between
    sections and tracks sibling headers at the same level. Valid Markdown headers should
    start with '#' followed by a space (e.g., "# Header 1", "## Header 2").
    The expresssion used to match headers is: `^(#+)\s+(.+)$`. If the header pattern in
    your text is different, you may need to adjust the `_header_pattern` attribute.

    Key Features:
        - Splits Markdown text into sections based on headers
        - Maintains parent-child relationships between headers
        - Tracks sibling headers at the same level
        - Handles code blocks correctly (ignores # in code)
        - Supports headers up to level 5 (##### H5)

    Example:
        >>> splitter = MarkdownSplitter()
        >>> text = '''
        ... # Introduction
        ... Markdown Splitting Made Easy.
        ... ## Installation
        ... To install the package, run the following command:
        ... ```python
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

    def __init__(self):
        self._header_pattern = re.compile(r"^(#+)\s+(.+)$", re.MULTILINE)

    def _process_code_blocks(self, text: str) -> tuple[str, dict[str, str]]:
        """Process code blocks to protect comments from being treated as headers."""
        replacement_map = {}
        counter = 0

        def replace_comments(match):
            nonlocal counter
            code_block = match.group(1)
            lines = code_block.split("\n")
            processed_lines = []

            for line in lines:
                if line.lstrip().startswith("#"):
                    token = f"{{{{CODE_COMMENT_{counter}}}}}"
                    replacement_map[token] = line
                    counter += 1
                    processed_lines.append(token)
                else:
                    processed_lines.append(line)

            return f"```{os.linesep.join(processed_lines)}```"

        processed_text = re.sub(
            r"```(?:.*?)\n(.*?)```", replace_comments, text, flags=re.DOTALL
        )
        return processed_text, replacement_map

    @classmethod
    def get_document_outline(cls, text: str) -> Dict:
        """Generate a nested document outline with header hierarchy and sibling relationships.

        Processes a Markdown document and creates a hierarchical structure that
        captures the relationships between headers, their content, and sibling headers at
        the same level.

        Args:
            text (str): The Markdown text to process. Should contain headers marked with '#'
                       (e.g., "# Header 1", "## Header 2", etc.).

        Returns:
            Dict: A nested dictionary representing the document structure where each node contains:
                - content (str): The text content under the header
                - level (int): The header level (1 for H1, 2 for H2, etc.)
                - children (Dict): Nested headers under this header
                - siblings (List[str]): Headers at the same level with the same parent

        Example:
            >>> text = '''
            ... # Header 1
            ... Content 1
            ... ## SubHeader A
            ... Content A
            ... ## SubHeader B
            ... Content B
            ... # Header 2
            ... Content 2
            ... '''
            >>> outline = MarkdownSplitter.get_document_outline(text)
            >>> outline
            {
                "Header 1": {
                    "content": "Content 1",
                    "level": 1,
                    "children": {
                        "SubHeader A": {
                            "content": "Content A",
                            "level": 2,
                            "children": {},
                            "siblings": ["SubHeader B"]
                        },
                        "SubHeader B": {
                            "content": "Content B",
                            "level": 2,
                            "children": {},
                            "siblings": ["SubHeader A"]
                        }
                    },
                    "siblings": ["Header 2"]
                },
                "Header 2": {
                    "content": "Content 2",
                    "level": 1,
                    "children": {},
                    "siblings": ["Header 1"]
                }
            }
        """
        if not text.strip():
            logger.warning("`get_document_outline` received empty text input.")
            return {}

        splitter = cls()
        processed_text, _ = splitter._process_code_blocks(text)
        headers = list(splitter._header_pattern.finditer(processed_text))

        if not headers:
            return {}

        # Initialize outline
        document_outline = {}
        header_stack = []
        current_path_stack = []

        # First pass: Build basic structure and collect siblings
        sibling_groups = {}  # Will store headers at same level with same immediate parent

        for i, match in enumerate(headers):
            header_marks, header_text = match.group(1), match.group(2).strip()
            current_level = len(header_marks)

            # Extract content
            start_pos = match.end()
            end_pos = headers[i + 1].start() if i + 1 < len(headers) else len(processed_text)
            content = processed_text[start_pos:end_pos].strip()

            # Create node
            current_node = {
                "content": content,
                "level": current_level,
                "children": {},
                "siblings": [],  # Will be populated later
            }

            # Update stacks based on current level
            while header_stack and header_stack[-1][0] >= current_level:
                header_stack.pop()
                if current_path_stack:
                    current_path_stack.pop()

            # Get immediate parent for sibling grouping
            immediate_parent = header_stack[-1][1] if header_stack else "root"
            sibling_group_key = (immediate_parent, current_level)

            # Track siblings
            if sibling_group_key not in sibling_groups:
                sibling_groups[sibling_group_key] = []
            sibling_groups[sibling_group_key].append(header_text)

            # Add node to document structure
            if not header_stack:  # Top level
                document_outline[header_text] = current_node
                current_path_stack = [header_text]
            else:
                current_parent = document_outline
                for path_element in current_path_stack:
                    current_parent = current_parent[path_element]["children"]
                current_parent[header_text] = current_node
                current_path_stack.append(header_text)

            header_stack.append((current_level, header_text))

        # Second pass: Add sibling information
        def add_siblings(outline: Dict, parent: str = "root", level: int = 1):
            for header, node in outline.items():
                sibling_group_key = (parent, node["level"])
                if sibling_group_key in sibling_groups:
                    node["siblings"] = [
                        h for h in sibling_groups[sibling_group_key] if h != header
                    ]
                add_siblings(node["children"], header, node["level"] + 1)

        add_siblings(document_outline)

        return document_outline

    def _create_sections_from_outline(
        self, outline: Dict, parent_headers: Dict[str, Optional[str]] = None
    ) -> List[Section]:
        """Convert a document outline into a flat list of Section objects with hierarchy information.

        Traverses the hierarchical document outline and creates Section objects and maintain
        the parent-child relationships and sibling connections. Recursively processes the outline
        to handle nested headers of any depth

        Args:
            outline (Dict): A nested dictionary representing the document structure. Each node should contain:
                - content (str): The text content under the header
                - level (int): The header level (1 for H1, 2 for H2, etc.)
                - children (Dict): Nested headers under this header
                - siblings (List[str]): Headers at the same level with the same parent
            parent_headers (Dict[str, Optional[str]], optional): A dictionary mapping header levels
                to their parent header text. Keys are in the format 'h1', 'h2', etc. Defaults to None,
                which initializes an empty parent hierarchy.

        Returns:
            List[Section]: A flat list of Section objects, each containing:
                - section_header (str): The header text
                - section_text (str): The content under the header
                - header_level (int): The level of the header
                - metadata (SectionMetadata): Contains parent headers and sibling information
        """
        if parent_headers is None:
            parent_headers = {f"h{i}": None for i in range(1, 5)}

        sections = []

        for header, node in outline.items():
            level = node["level"]
            content = node["content"]

            # Create metadata with parents and siblings
            metadata = SectionMetadata(
                parents={k: v for k, v in parent_headers.items() if v is not None},
                siblings=node["siblings"],
            )

            # Create section
            section = Section(
                section_header=header,
                section_text=content,
                header_level=level,
                metadata=metadata,
            )
            sections.append(section)

            # Update parent headers for children
            new_parents = parent_headers.copy()
            new_parents[f"h{level}"] = header

            # Process children
            child_sections = self._create_sections_from_outline(node["children"], new_parents)
            sections.extend(child_sections)

        return sections

    def split_text(self, text: str) -> List[Section]:
        """Split Markdown text into sections while maintaining header hierarchy.

        Processes a Markdown document and splits it into sections based on
        headers. It maintains the hierarchical relationships between sections and tracks
        sibling headers at the same level. The parent headers are tracked up to level 5 (h1-h5).
        And, sibling relationships are based on headers at the same level with the same immediate parent.
        Comments in code blocks (```) are not treated as headers.

        Args:
            text (str): The Markdown text to split. Should contain headers marked with '#'
                       followed by a space (e.g., "# Header 1", "## Header 2").

        Returns:
            List[Section]: A list of Section objects, each containing:
                - section_header (str): The header text without '#' markers
                - section_text (str): The content between this header and the next
                - header_level (int): The level of the header (1 for H1, 2 for H2, etc.)
                - metadata (SectionMetadata): Contains:
                    - parents (Dict[str, str]): Parent headers by level
                    - siblings (List[str]): Other headers at same level with same parent

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

        # Get document outline
        outline = self.get_document_outline(text)

        # Create sections from outline
        sections = self._create_sections_from_outline(outline)

        logger.info(f"Successfully split the Markdown into {len(sections)} sections.")
        return sections

    @classmethod
    def from_file(cls, filepath: Union[str, Path], encoding: str = "utf-8") -> List[Section]:
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
            splitter = cls()
            with path.open("r", encoding=encoding) as f:
                return splitter.split_text(f.read())
        except Exception as e:
            logger.error(
                f"Failed to split the Markdown file: {path}. Error: {str(e)}", exc_info=True
            )
            raise
