"""
Security regression tests.
Run: python -m pytest code/tests/test_secrets.py -q
"""

import os
import pathlib

# The planted demo secret — must never appear in committed files
PLANTED_SECRET = "sk-demo-4f8a2b1c9d3e7f6a"
REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent


def test_no_env_file_committed():
    """Real .env should not exist in the repo root (it's git-ignored)."""
    env_path = REPO_ROOT / ".env"
    if env_path.exists():
        content = env_path.read_text()
        # It's okay to have .env locally, but it must not contain a real token
        assert "hf_YOUR" in content or len(content.strip()) == 0 or "HF_TOKEN" not in content, \
            ".env contains what looks like a real HF_TOKEN"


def test_no_secret_in_readme():
    """The planted secret should not appear in README."""
    readme = REPO_ROOT / "README.md"
    if readme.exists():
        assert PLANTED_SECRET not in readme.read_text(), \
            "Planted secret found in README.md!"


def test_env_example_has_placeholder():
    """The .env.example should have a placeholder, not a real token."""
    env_example = REPO_ROOT / ".env.example"
    if env_example.exists():
        content = env_example.read_text()
        assert "hf_YOUR" in content, \
            ".env.example should have placeholder token"
