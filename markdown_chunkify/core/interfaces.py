from abc import ABC
from abc import abstractmethod
from pathlib import Path
from typing import Generic
from typing import TypeVar

T = TypeVar("T")


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


class BaseProcessor(ABC, Generic[T]):
    @abstractmethod
    def process_text(self, section: T) -> T:
        """Normalize Unicode characters.

        Args:
            content: Content to normalize

        Returns:s
            Normalized content of the same type

        Raises:
            NormalizationError: If normalization fails
        """
        pass
