import pytest

from markdown_chunkify.utils.splitters import MarkdownSplitter


@pytest.fixture
def splitter():
    return MarkdownSplitter()


@pytest.fixture
def sample_markdown():
    return """# Header 1
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
Content 2.1.1"""


@pytest.fixture
def nested_markdown():
    return """# Main
Content
## Sub
Sub content
### Deep
Deep content"""
