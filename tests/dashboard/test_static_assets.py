"""Tests for dashboard static asset contracts."""

from pathlib import Path

STATIC_DIR = Path("dashboard/static")


class TestDashboardMarkup:
    def test_when_rendering_defender_metrics_expect_required_elements(self) -> None:
        # arrange
        index_html = (STATIC_DIR / "index.html").read_text()

        # act / assert
        assert 'id="blockMetric"' in index_html
        assert 'id="blockRateMetric"' in index_html
