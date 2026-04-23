import os
import tempfile

import pytest
from fastapi import HTTPException

from main import find_md


def test_find_md_returns_path():
    with tempfile.TemporaryDirectory() as tmpdir:
        md_path = os.path.join(tmpdir, "doc.md")
        with open(md_path, "w") as f:
            f.write("# Hello")
        assert find_md(tmpdir) == md_path


def test_find_md_no_file_raises_400():
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "file.txt"), "w") as f:
            f.write("not markdown")
        with pytest.raises(HTTPException) as exc:
            find_md(tmpdir)
        assert exc.value.status_code == 400


def test_find_md_multiple_files_raises_400():
    with tempfile.TemporaryDirectory() as tmpdir:
        for name in ("a.md", "b.md"):
            with open(os.path.join(tmpdir, name), "w") as f:
                f.write("# doc")
        with pytest.raises(HTTPException) as exc:
            find_md(tmpdir)
        assert exc.value.status_code == 400


def test_find_md_nested_directory():
    with tempfile.TemporaryDirectory() as tmpdir:
        subdir = os.path.join(tmpdir, "sub", "nested")
        os.makedirs(subdir)
        md_path = os.path.join(subdir, "deep.md")
        with open(md_path, "w") as f:
            f.write("# Nested")
        assert find_md(tmpdir) == md_path


def test_find_md_ignores_non_md_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        md_path = os.path.join(tmpdir, "only.md")
        with open(md_path, "w") as f:
            f.write("# Only MD")
        for name in ("image.png", "data.csv", "script.py"):
            with open(os.path.join(tmpdir, name), "w") as f:
                f.write("other")
        assert find_md(tmpdir) == md_path


def test_find_md_empty_dir_raises_400():
    with tempfile.TemporaryDirectory() as tmpdir:
        with pytest.raises(HTTPException) as exc:
            find_md(tmpdir)
        assert exc.value.status_code == 400
