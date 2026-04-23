import io
import os
import tempfile
import zipfile
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from main import extract_archive


@pytest.mark.asyncio
async def test_extract_valid_zip():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("document.md", "# Hello")
        zf.writestr("image.png", b"\x89PNG")
    buf.seek(0)

    archive = AsyncMock()
    archive.read.return_value = buf.getvalue()

    with tempfile.TemporaryDirectory() as tmpdir:
        await extract_archive(archive, tmpdir)
        assert os.path.exists(os.path.join(tmpdir, "document.md"))
        assert os.path.exists(os.path.join(tmpdir, "image.png"))


@pytest.mark.asyncio
async def test_extract_invalid_zip_raises_400():
    archive = AsyncMock()
    archive.read.return_value = b"this is not a zip file at all"

    with tempfile.TemporaryDirectory() as tmpdir:
        with pytest.raises(HTTPException) as exc:
            await extract_archive(archive, tmpdir)
        assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_extract_empty_zip():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w"):
        pass  # empty archive
    buf.seek(0)

    archive = AsyncMock()
    archive.read.return_value = buf.getvalue()

    with tempfile.TemporaryDirectory() as tmpdir:
        await extract_archive(archive, tmpdir)
        # extraction succeeds, directory is just empty
        assert os.path.isdir(tmpdir)


@pytest.mark.asyncio
async def test_extract_preserves_directory_structure():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("subdir/nested.md", "# Nested")
    buf.seek(0)

    archive = AsyncMock()
    archive.read.return_value = buf.getvalue()

    with tempfile.TemporaryDirectory() as tmpdir:
        await extract_archive(archive, tmpdir)
        assert os.path.exists(os.path.join(tmpdir, "subdir", "nested.md"))
