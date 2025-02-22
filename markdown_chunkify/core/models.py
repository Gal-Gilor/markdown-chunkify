import re

from pydantic import BaseModel
from pydantic import Field
from pydantic import field_validator


class MarkdownContent(BaseModel):
    """Represents a Markdown section with a header and content."""

    section_header: str = Field(..., description="The Markdown section header")
    section_text: str = Field(..., description="The Markdown section content")

    @field_validator("section_header")
    def clean_section_header(cls, value):
        """Remove leading and trailing whitespace from the section header."""
        return re.sub(r"^#+\s*", "", value)


class SectionMetadata(BaseModel):
    """Metadata fields for a Markdown section."""

    token_count: int | None = Field(None, description="Generation token count")
    model_version: str | None = Field(None, description="The model that was used.")
    normalized: bool = Field(
        False, description="Flag indicating if the content is normalized"
    )
    error: str | None = Field(None, description="Error message if normalization failed")
    original_content: MarkdownContent | None = Field(
        None, description="The original section content if thew section was normalized"
    )
    parents: dict[str, str | None] = Field(
        default_factory=dict,
        description="Parent headers hierarchy for the section",
    )
    siblings: list[str] = Field(
        default_factory=list,
        description="List of sibling section headers at the same level with same parent",
    )


class Section(MarkdownContent):
    """Represents a section in a Markdown document with its header hierarchy."""

    header_level: int = Field(..., description="The level of the header (number of #)")
    metadata: SectionMetadata = Field(
        default_factory=SectionMetadata,
        description="The Markdown section metadata.",
    )

    def to_markdown(self) -> str:
        """Convert the section to a Markdown string."""
        return f"{'#' * self.header_level} {self.section_header}\n\n{self.section_text}"
