from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import computed_field


class SectionMetadata(BaseModel):
    """Metadata fields for a Markdown section."""

    model_config = ConfigDict(frozen=True)

    id: int = Field(
        ..., description="The section's position in document order, starting at 0"
    )
    parent_id: int | None = Field(
        None, description="The id of the enclosing section. None for top-level sections"
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


class Section(BaseModel):
    """Represents a section in a Markdown document with its header hierarchy."""

    model_config = ConfigDict(frozen=True)

    header: str = Field(..., description="The Markdown section header")
    content: str = Field(..., description="The Markdown section content")
    level: int = Field(
        ...,
        ge=0,
        description=(
            "The level of the header (number of #). 0 for text before the first header."
        ),
    )
    metadata: SectionMetadata = Field(..., description="The Markdown section metadata.")

    def to_markdown(self) -> str:
        """Convert the section to a Markdown string."""
        if self.level == 0:
            return self.content
        return f"{'#' * self.level} {self.header}\n\n{self.content}"

    def breadcrumb(self, separator: str = " > ") -> str:
        """Join the parent headers and the section's own header, such as 'Docker > Setup'.

        Text before the first header has no headers and returns an empty string.
        """
        return separator.join([*self.metadata.parents.values(), self.header])
