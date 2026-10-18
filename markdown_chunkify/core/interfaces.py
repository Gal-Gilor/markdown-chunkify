from abc import ABC
from abc import abstractmethod

from markdown_chunkify.core.models import Section


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
