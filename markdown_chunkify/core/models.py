from pydantic import BaseModel
from pydantic import Field


class MarkdownContent(BaseModel):
    """Represents a Markdown section with a header and content."""

    section_header: str = Field(..., description="The Markdown section header")
    section_text: str = Field(..., description="The Markdown section content")


class SectionMetadata(BaseModel):
    """Metadata fields for a Markdown section."""

    normalized: bool = Field(
        False,
        description="Whether Unicode normalization changed the section header or text",
    )
    parents: dict[str, str | None] = Field(
        default_factory=dict,
        description="Parent headers hierarchy for the section",
    )
    siblings: list[str] = Field(
        default_factory=list,
        description="List of sibling section headers at the same level with same parent",
    )
    span: tuple[int, int] | None = Field(
        None,
        description=(
            "The start (inclusive) and end (exclusive) character offsets of the section, "
            "header line included, in the source text"
        ),
    )
    char_count: int | None = Field(
        None, description="The number of characters in the section's span"
    )


class Section(MarkdownContent):
    """Represents a section in a Markdown document with its header hierarchy."""

    header_level: int = Field(
        ...,
        ge=0,
        description=(
            "The level of the header (number of #). 0 for text before the first header."
        ),
    )
    metadata: SectionMetadata = Field(
        default_factory=SectionMetadata,
        description="The Markdown section metadata.",
    )

    def to_markdown(self) -> str:
        """Convert the section to a Markdown string."""
        if self.header_level == 0:
            return self.section_text
        return f"{'#' * self.header_level} {self.section_header}\n\n{self.section_text}"
