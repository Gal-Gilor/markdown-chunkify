import json
from dataclasses import asdict
from dataclasses import dataclass

from pydantic import BaseModel
from pydantic import Field


class NormalizedSection(BaseModel):
    """Data model containing a text string."""

    section_header: str = Field(..., description="The Markdown section header")
    section_text: str = Field(..., description="The Markdown section content")


@dataclass
class MarkdownSection:
    """Represents a section in a Markdown document with its header hierarchy."""

    section_header: str
    section_text: str
    header_level: int
    metadata: dict[str, dict[str, str | None]]

    @classmethod
    def create(
        cls,
        header: str,
        text: str,
        header_level: int,
        parent_headers: dict[str, str | None],
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
