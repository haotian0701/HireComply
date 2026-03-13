"""Tests for the resume parser tool."""

from pathlib import Path
import tempfile

from src.tools.resume_parser import parse_resume


class TestResumeParser:
    """Test suite for resume parsing."""

    def test_parse_txt_resume(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Alice Zhang\nSenior Software Engineer\n5 years Python")
            f.flush()

            result = parse_resume(f.name)
            assert "Alice Zhang" in result["text"]
            assert result["file_type"] == "txt"
            assert result["page_count"] == 1

    def test_unsupported_format_raises(self):
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            try:
                parse_resume(f.name)
                assert False, "Should have raised ValueError"
            except ValueError as e:
                assert "Unsupported" in str(e)

    def test_missing_file_raises(self):
        try:
            parse_resume("/nonexistent/resume.pdf")
            assert False, "Should have raised FileNotFoundError"
        except FileNotFoundError:
            pass
