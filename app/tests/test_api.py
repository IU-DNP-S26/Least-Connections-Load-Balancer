import io
import os
import tempfile
import zipfile
from unittest.mock import patch

import pytest
from httpx import AsyncClient, ASGITransport

from main import app


def make_zip(files: dict) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buf.getvalue()


@pytest.mark.asyncio
async def test_health_returns_200():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_convert_non_zip_returns_400():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/convert/md/to-pdf",
            files={"archive": ("doc.txt", b"hello", "text/plain")},
        )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_convert_invalid_zip_returns_400():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/convert/md/to-pdf",
            files={"archive": ("archive.zip", b"not a zip", "application/zip")},
        )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_convert_no_md_returns_400():
    zip_bytes = make_zip({"readme.txt": "no markdown here"})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/convert/md/to-pdf",
            files={"archive": ("archive.zip", zip_bytes, "application/zip")},
        )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_convert_multiple_md_returns_400():
    zip_bytes = make_zip({"a.md": "# A", "b.md": "# B"})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/convert/md/to-pdf",
            files={"archive": ("archive.zip", zip_bytes, "application/zip")},
        )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_convert_valid_md_returns_pdf():
    zip_bytes = make_zip({"document.md": "# Hello World\n\nTest content."})

    with tempfile.TemporaryDirectory() as tmpdir:
        fake_pdf = os.path.join(tmpdir, "result.pdf")
        with open(fake_pdf, "wb") as f:
            f.write(b"%PDF-1.4 fake content")

        with patch("main.convert_to_pdf", return_value=fake_pdf):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/convert/md/to-pdf",
                    files={"archive": ("archive.zip", zip_bytes, "application/zip")},
                )

    assert response.status_code == 200
    assert "application/pdf" in response.headers["content-type"]


@pytest.mark.asyncio
async def test_convert_result_filename_matches_md():
    zip_bytes = make_zip({"my_report.md": "# Report"})

    with tempfile.TemporaryDirectory() as tmpdir:
        fake_pdf = os.path.join(tmpdir, "my_report.pdf")
        with open(fake_pdf, "wb") as f:
            f.write(b"%PDF-1.4 fake")

        with patch("main.convert_to_pdf", return_value=fake_pdf):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/convert/md/to-pdf",
                    files={"archive": ("archive.zip", zip_bytes, "application/zip")},
                )

    assert response.status_code == 200
    cd = response.headers.get("content-disposition", "")
    assert "my_report.pdf" in cd
