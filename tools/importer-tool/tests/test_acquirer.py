import pytest

from app.services.acquirer import acquire_text
from app.services.classifier import _extract_title


@pytest.mark.asyncio
async def test_acquire_text():
    result = await acquire_text("Hello World", "test.txt")
    assert result.content == "Hello World"
    assert result.filename == "test.txt"
    assert result.mime_type == "text/plain"


@pytest.mark.asyncio
async def test_acquire_text_truncation():
    long_text = "x" * 200000
    result = await acquire_text(long_text)
    assert len(result.content) <= 100000


@pytest.mark.asyncio
async def test_checksum_consistency():
    r1 = await acquire_text("same content")
    r2 = await acquire_text("same content")
    assert r1.checksum == r2.checksum


@pytest.mark.asyncio
async def test_checksum_different():
    r1 = await acquire_text("content a")
    r2 = await acquire_text("content b")
    assert r1.checksum != r2.checksum


def test_extract_title_markdown():
    title = _extract_title("# My Title\n\nbody")
    assert title == "My Title"


def test_extract_title_first_heading():
    title = _extract_title("preamble\n## Second\n# First")
    assert title == "First"


def test_extract_title_no_heading():
    title = _extract_title("plain text", "my-document.md")
    assert title == "My Document"


def test_extract_title_filename_only():
    title = _extract_title("", "readme.md")
    assert title == "readme.md"  # empty content returns filename as-is
