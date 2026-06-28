"""Tests for event emitter run directory creation."""

import os
from pathlib import Path

from common.src.event_emitter import EVENTS_FILENAME, create_run_dir


class TestCreateRunDir:
    def test_when_called_expect_timestamped_dir_and_events_file_path(self, tmp_path: Path) -> None:
        # act
        result = create_run_dir(tmp_path)

        # assert
        assert result.name == EVENTS_FILENAME
        assert result.parent.parent == tmp_path
        assert result.parent.is_dir()

    def test_when_called_expect_latest_symlink_points_to_run_dir(self, tmp_path: Path) -> None:
        # act
        result = create_run_dir(tmp_path)

        # assert
        latest = tmp_path / "latest"
        assert latest.is_symlink()
        assert os.readlink(latest) == result.parent.name

    def test_when_called_twice_expect_latest_symlink_points_to_second_run(self, tmp_path: Path) -> None:
        # act
        first = create_run_dir(tmp_path)
        second = create_run_dir(tmp_path)

        # assert
        latest = tmp_path / "latest"
        assert os.readlink(latest) == second.parent.name
        assert first.parent.is_dir()
        assert second.parent.is_dir()

    def test_when_events_dir_does_not_exist_expect_created(self, tmp_path: Path) -> None:
        # arrange
        events_dir = tmp_path / "nested" / "events"

        # act
        result = create_run_dir(events_dir)

        # assert
        assert result.parent.is_dir()
        assert events_dir.is_dir()
