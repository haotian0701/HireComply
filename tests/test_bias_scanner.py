"""Tests for the rule-based bias detector."""

from src.tools.bias_detector import detect_bias, get_bias_summary


class TestBiasDetector:
    """Test suite for bias detection rules."""

    def test_no_bias_in_clean_jd(self):
        clean_jd = """
        Software Engineer — Python
        We are looking for a skilled software engineer with 3+ years
        of Python experience. The role involves building backend services
        using FastAPI and PostgreSQL. Fluent English required.
        """
        matches = detect_bias(clean_jd)
        # Should have minimal or no flags
        high_flags = [m for m in matches if m.severity == "high"]
        assert len(high_flags) == 0

    def test_detects_age_bias(self):
        biased_jd = "Looking for a young and dynamic digital native"
        matches = detect_bias(biased_jd)
        types = {m.bias_type for m in matches}
        assert "age" in types
        high = [m for m in matches if m.severity == "high"]
        assert len(high) >= 1  # "young" and "digital native" are high

    def test_detects_gender_bias(self):
        biased_jd = "He should be aggressive in pursuing new clients"
        matches = detect_bias(biased_jd)
        types = {m.bias_type for m in matches}
        assert "gender" in types

    def test_detects_socioeconomic_bias(self):
        biased_jd = "Degree from a top-tier university required"
        matches = detect_bias(biased_jd)
        types = {m.bias_type for m in matches}
        assert "socioeconomic" in types

    def test_detects_ethnicity_bias(self):
        biased_jd = "Must be a native English speaker"
        matches = detect_bias(biased_jd)
        types = {m.bias_type for m in matches}
        assert "ethnicity" in types

    def test_detects_disability_bias(self):
        biased_jd = "Candidate must be physically fit and able-bodied"
        matches = detect_bias(biased_jd)
        types = {m.bias_type for m in matches}
        assert "disability" in types

    def test_suggestions_provided(self):
        biased_jd = "Looking for a young digital native"
        matches = detect_bias(biased_jd)
        for m in matches:
            assert m.suggestion, f"No suggestion for rule {m.rule_id}"

    def test_summary_risk_level_high(self):
        biased_jd = "Young digital native from a top-tier university"
        matches = detect_bias(biased_jd)
        summary = get_bias_summary(matches)
        assert summary["risk_level"] == "high"

    def test_summary_risk_level_low(self):
        matches = []
        summary = get_bias_summary(matches)
        assert summary["risk_level"] == "low"
        assert summary["total_flags"] == 0

    def test_sample_jd_from_run_pipeline(self):
        """Test the intentionally biased sample JD from run_pipeline.py."""
        sample_jd = """
        We are looking for a young and dynamic software engineer to join our
        fast-paced team. The ideal candidate is a digital native who thrives
        in a high-energy startup environment.
        Bachelor's degree from a top-tier university
        """
        matches = detect_bias(sample_jd)
        summary = get_bias_summary(matches)

        # Should catch: young, dynamic, digital native, top-tier university
        assert summary["total_flags"] >= 3
        assert summary["risk_level"] == "high"
        assert "age" in summary["by_type"]
        assert "socioeconomic" in summary["by_type"]
