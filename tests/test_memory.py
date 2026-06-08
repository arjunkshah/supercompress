"""Tests for SuperCompress memory layer."""

from supercompress import compress_context, compare_policies


def test_compress_reduces_tokens():
    text = "def foo():\n    return 42\n\n" * 50
    text += "class Bar:\n    pass\n"
    result = compress_context(text, "where is foo defined", budget_ratio=0.35)
    assert result.kept_tokens < result.original_tokens
    assert "foo" in result.compressed_text or "def" in result.compressed_text


def test_compare_policies():
    text = "def authenticate(user):\n    return user\n" * 30
    cmp = compare_policies(text, "authenticate", budget_ratio=0.35)
    assert "FIFO" in cmp
    assert "SuperCompress" in cmp
