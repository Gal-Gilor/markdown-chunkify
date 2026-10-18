from pydantic import BaseModel
from pydantic import Field
from pydantic import computed_field


class MarkdownContent(BaseModel):
    """Represents a Markdown section with a header and content."""

    section_header: str = Field(..., description="The Markdown section header")
    section_text: str = Field(..., description="The Markdown section content")


class SectionMetadata(BaseModel):
    """Metadata fields for a Markdown section."""

    id: int | None = Field(
        None, description="The section's position in document order, starting at 0"
    )
    parent_id: int | None = Field(
        None, description="The id of the enclosing section. None for top-level sections"
    )
    normalized: bool = Field(
        False,
        description="Whether Unicode normalization changed the section header or text",
    )
    parents: dict[str, str] = Field(
        default_factory=dict,
        description="Parent headers hierarchy for the section",
    )
    span: tuple[int, int] = Field(
        ...,
        description=(
            "The start (inclusive) and end (exclusive) character offsets of the section, "
            "header line included, in the source text"
        ),
    )

    @computed_field
    @property
    def char_count(self) -> int:
        """The number of characters in the section's span."""
        return self.span[1] - self.span[0]


class Section(MarkdownContent):
    """Represents a section in a Markdown document with its header hierarchy."""

    header_level: int = Field(
        ...,
        ge=0,
        description=(
            "The level of the header (number of #). 0 for text before the first header."
        ),
    )
    metadata: SectionMetadata = Field(..., description="The Markdown section metadata.")

    def to_markdown(self) -> str:
        """Convert the section to a Markdown string."""
        if self.header_level == 0:
            return self.section_text
        return f"{'#' * self.header_level} {self.section_header}\n\n{self.section_text}"

    def breadcrumb(self, separator: str = " > ") -> str:
        """Join the parent headers and the section's own header, such as 'Docker > Setup'.

        Text before the first header has no headers and returns an empty string.
        """
        return separator.join([*self.metadata.parents.values(), self.section_header])


class OutlineNode(BaseModel):
    """A header and its content in a document outline, with its nested headers."""

    header: str = Field(
        ..., description="The header text. Empty for text before the first header"
    )
    content: str = Field(..., description="The text under the header, up to the next header")
    level: int = Field(
        ...,
        ge=0,
        description=(
            "The level of the header (number of #). 0 for text before the first header."
        ),
    )
    id: int = Field(..., description="The node's position in document order, starting at 0")
    parent_id: int | None = Field(
        ..., description="The id of the enclosing node. None for top-level nodes"
    )
    span: tuple[int, int] = Field(
        ...,
        description=(
            "The start (inclusive) and end (exclusive) character offsets of the node, "
            "header line included, in the source text"
        ),
    )
    children: list["OutlineNode"] = Field(
        default_factory=list,
        description="The nodes of the headers nested under this header, in document order",
    )
