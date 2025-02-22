from textwrap import dedent

import pytest

from markdown_chunkify.components.splitters import MarkdownSplitter


@pytest.fixture
def splitter():
    return MarkdownSplitter()


@pytest.fixture
def sample_markdown():
    return dedent(
        """
        # Header 1
        Content 1
        ## Header 1.1
        Content 1.1
        # Header 2
        Content 2
        ## Header 2.1
        Content 2.1
        ```python
        # Code block comment
        ```
        ### Header 2.1.1
        Content 2.1.1
        ## Header 2.2
        Content 2.2"""
    )


@pytest.fixture
def nested_markdown():
    return dedent(
        """
        # Main
        Content
        ## Sub
        Sub content
        ### Deep
        Deep content
        ## Sub 2
        Sub content 2
        """
    )
