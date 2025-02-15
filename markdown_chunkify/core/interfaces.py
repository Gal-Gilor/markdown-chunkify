from abc import ABC
from abc import abstractmethod
from pathlib import Path


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
    def split_text(self, text: str) -> list[str]:
        """Split text into chunks.

        Args:
            text: Text to split

        Returns:
            list[Any]: List of objects containing the split text, or the split text itself.
        """
        pass


class BaseNormalizer(ABC):
    @abstractmethod
    def normalize_unicode(self, text: str) -> str:
        """Convert Unicode characters to ASCII equivalents.

        Args:
            text: String containing Unicode characters

        Returns:
            String with normalized Unicode characters
        """
        pass
