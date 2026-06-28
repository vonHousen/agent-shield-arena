"""Tests for the dashboard FastAPI application."""

import os
from pathlib import Path

from fastapi.testclient import TestClient

from common.src.event_emitter import EVENTS_FILENAME
from dashboard.src.app import create_app


class TestListRuns:
    def test_when_no_runs_exist_expect_empty_list(self, tmp_path: Path) -> None:
        # arrange
        client = TestClient(create_app(events_dir=tmp_path))

        # act
        response = client.get("/api/runs")

        # assert
        assert response.status_code == 200
        assert response.json() == []

    def test_when_events_dir_missing_expect_empty_list(self, tmp_path: Path) -> None:
        # arrange
        missing = tmp_path / "nonexistent"
        client = TestClient(create_app(events_dir=missing))

        # act
        response = client.get("/api/runs")

        # assert
        assert response.status_code == 200
        assert response.json() == []

    def test_when_two_runs_exist_expect_sorted_newest_first(self, tmp_path: Path) -> None:
        # arrange
        older_name = "20260627_100000"
        newer_name = "20260627_120000"
        _create_run_dir(tmp_path, older_name)
        _create_run_dir(tmp_path, newer_name)
        client = TestClient(create_app(events_dir=tmp_path))

        # act
        response = client.get("/api/runs")

        # assert
        runs = response.json()
        assert len(runs) == 2
        assert runs[0]["id"] == newer_name
        assert runs[1]["id"] == older_name

    def test_when_latest_symlink_exists_expect_excluded_from_runs(self, tmp_path: Path) -> None:
        # arrange
        run_name = "20260627_100000"
        _create_run_dir(tmp_path, run_name)
        os.symlink(run_name, tmp_path / "latest")
        client = TestClient(create_app(events_dir=tmp_path))

        # act
        response = client.get("/api/runs")

        # assert
        runs = response.json()
        assert len(runs) == 1
        assert runs[0]["id"] == run_name

    def test_when_dir_has_no_events_file_expect_excluded(self, tmp_path: Path) -> None:
        # arrange
        (tmp_path / "20260627_100000").mkdir()
        client = TestClient(create_app(events_dir=tmp_path))

        # act
        response = client.get("/api/runs")

        # assert
        assert response.json() == []

    def test_when_run_exists_expect_iso_timestamp_in_response(self, tmp_path: Path) -> None:
        # arrange
        run_name = "20260627_143022"
        _create_run_dir(tmp_path, run_name)
        client = TestClient(create_app(events_dir=tmp_path))

        # act
        response = client.get("/api/runs")

        # assert
        runs = response.json()
        assert runs[0]["timestamp"] == "2026-06-27T14:30:22"


def _create_run_dir(events_dir: Path, name: str) -> Path:
    """Create a fake run directory with an empty events file."""
    run_dir = events_dir / name
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / EVENTS_FILENAME).touch()
    return run_dir
