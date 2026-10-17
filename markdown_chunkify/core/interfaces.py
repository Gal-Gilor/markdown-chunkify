from abc import ABC
from abc import abstractmethod
from pathlib import Path

from markdown_chunkify.core.models import Section


class BaseParser(ABC):
    @abstractmethod
    def to_markdown(self, file_path: str | Path) -> str:
        """Parse file to markdown text.

        Args:
            file_path: Path to the file

        Returns:
            str: A Markdown formatted text.
        """
        pass


class BaseSplitter(ABC):
    @abstractmethod
    def split_text(self, text: str) -> list[Section]:
        """Split text into sections.

        Args:
            text: Text to split

        Returns:
            list[Section]: The sections of the text in document order.
        """
        pass
