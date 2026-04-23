import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from converters.md_to_pdf import HighlightRenderer, adaptive_image_sizes, convert_to_pdf


# ── HighlightRenderer ────────────────────────────────────────────────────────

def test_highlight_renderer_with_python():
    renderer = HighlightRenderer()
    result = renderer.block_code('print("hello")', "python")
    assert "highlight" in result
    assert "hello" in result


def test_highlight_renderer_unknown_language_falls_back():
    renderer = HighlightRenderer()
    # Should not raise — falls back to TextLexer
    result = renderer.block_code("some code", "totally_unknown_language_xyz")
    assert result
    assert "some code" in result


def test_highlight_renderer_no_language():
    renderer = HighlightRenderer()
    result = renderer.block_code("plain text", None)
    assert result
    assert "plain text" in result


def test_highlight_renderer_empty_code():
    renderer = HighlightRenderer()
    result = renderer.block_code("", "python")
    assert result is not None


# ── adaptive_image_sizes ─────────────────────────────────────────────────────

def test_adaptive_image_sizes_no_images():
    html = "<p>No images here</p>"
    result = adaptive_image_sizes(html, "/tmp")
    assert "No images here" in result


def test_adaptive_image_sizes_missing_image_gets_fallback():
    html = '<img src="nonexistent.png"/>'
    result = adaptive_image_sizes(html, "/tmp")
    assert "max-width: 100%" in result


def test_adaptive_image_sizes_small_image():
    with tempfile.TemporaryDirectory() as tmpdir:
        mock_img = MagicMock()
        mock_img.size = (400, 300)  # width < 600 → 50%
        mock_cm = MagicMock()
        mock_cm.__enter__ = MagicMock(return_value=mock_img)
        mock_cm.__exit__ = MagicMock(return_value=False)

        with patch("converters.md_to_pdf.Image") as mock_pil:
            mock_pil.open.return_value = mock_cm
            result = adaptive_image_sizes('<img src="small.png"/>', tmpdir)

        assert "width: 50%" in result


def test_adaptive_image_sizes_medium_image():
    with tempfile.TemporaryDirectory() as tmpdir:
        mock_img = MagicMock()
        mock_img.size = (800, 600)  # 600 ≤ width < 1000 → 70%
        mock_cm = MagicMock()
        mock_cm.__enter__ = MagicMock(return_value=mock_img)
        mock_cm.__exit__ = MagicMock(return_value=False)

        with patch("converters.md_to_pdf.Image") as mock_pil:
            mock_pil.open.return_value = mock_cm
            result = adaptive_image_sizes('<img src="medium.png"/>', tmpdir)

        assert "width: 70%" in result


def test_adaptive_image_sizes_large_image():
    with tempfile.TemporaryDirectory() as tmpdir:
        mock_img = MagicMock()
        mock_img.size = (2000, 1000)  # width ≥ 1600 → 100%
        mock_cm = MagicMock()
        mock_cm.__enter__ = MagicMock(return_value=mock_img)
        mock_cm.__exit__ = MagicMock(return_value=False)

        with patch("converters.md_to_pdf.Image") as mock_pil:
            mock_pil.open.return_value = mock_cm
            result = adaptive_image_sizes('<img src="large.png"/>', tmpdir)

        assert "width: 100%" in result


# ── convert_to_pdf ───────────────────────────────────────────────────────────

def test_convert_to_pdf_returns_pdf_path():
    with tempfile.TemporaryDirectory() as tmpdir:
        md_path = os.path.join(tmpdir, "test.md")
        with open(md_path, "w") as f:
            f.write("# Test\n\nHello world.\n\n```python\nprint('hi')\n```")

        output_path = None

        def fake_write_pdf(path, **kw):
            nonlocal output_path
            output_path = path
            with open(path, "wb") as f:
                f.write(b"%PDF-1.4")

        with patch("converters.md_to_pdf.HTML") as mock_html, \
             patch("converters.md_to_pdf.CSS"):
            mock_html.return_value.write_pdf.side_effect = fake_write_pdf
            result = convert_to_pdf(md_path)

        assert result.endswith(".pdf")

        if output_path and os.path.exists(output_path):
            os.remove(output_path)


def test_convert_to_pdf_passes_base_url():
    with tempfile.TemporaryDirectory() as tmpdir:
        md_path = os.path.join(tmpdir, "test.md")
        with open(md_path, "w") as f:
            f.write("# Simple")

        with patch("converters.md_to_pdf.HTML") as mock_html, \
             patch("converters.md_to_pdf.CSS"):
            mock_html.return_value.write_pdf.side_effect = lambda path, **kw: open(path, "wb").write(b"%PDF")

            result = convert_to_pdf(md_path)

            call_kwargs = mock_html.call_args
            assert "base_url" in call_kwargs.kwargs
            assert tmpdir in call_kwargs.kwargs["base_url"]

        if os.path.exists(result):
            os.remove(result)
