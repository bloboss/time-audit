"""Tests for CLI commands."""

import tempfile
from datetime import datetime
from pathlib import Path

import pytest  # type: ignore[import-not-found]
from click.testing import CliRunner  # type: ignore[import-not-found]

from time_audit.cli.main import cli
from time_audit.core.storage import StorageManager


@pytest.fixture  # type: ignore[misc]
def runner() -> CliRunner:
    """Create CLI test runner."""
    return CliRunner()


@pytest.fixture  # type: ignore[misc]
def temp_dir() -> Path:
    """Create temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


class TestCLICommands:
    """Test CLI commands."""

    def test_version(self, runner: CliRunner) -> None:
        """Test --version flag."""
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "0.2.0" in result.output

    def test_help(self, runner: CliRunner) -> None:
        """Test --help flag."""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Time Audit" in result.output

    def test_start_command(self, runner: CliRunner, temp_dir: Path) -> None:
        """Test start command."""
        result = runner.invoke(
            cli,
            ["--data-dir", str(temp_dir), "start", "Test task"],
        )

        assert result.exit_code == 0
        assert "Started tracking" in result.output
        assert "Test task" in result.output

    def test_start_with_options(self, runner: CliRunner, temp_dir: Path) -> None:
        """Test start command with all options."""
        result = runner.invoke(
            cli,
            [
                "--data-dir",
                str(temp_dir),
                "start",
                "Test task",
                "-p",
                "test-project",
                "-c",
                "development",
                "-t",
                "tag1,tag2",
                "-n",
                "Test notes",
            ],
        )

        assert result.exit_code == 0
        assert "test-project" in result.output

    def test_start_when_already_running(self, runner: CliRunner, temp_dir: Path) -> None:
        """Test start command fails when already running."""
        # Start first task
        runner.invoke(cli, ["--data-dir", str(temp_dir), "start", "First task"])

        # Try to start second task
        result = runner.invoke(cli, ["--data-dir", str(temp_dir), "start", "Second task"])

        assert result.exit_code == 1
        assert "Error" in result.output

    def test_stop_command(self, runner: CliRunner, temp_dir: Path) -> None:
        """Test stop command."""
        # Start a task first
        runner.invoke(cli, ["--data-dir", str(temp_dir), "start", "Test task"])

        # Stop it
        result = runner.invoke(cli, ["--data-dir", str(temp_dir), "stop"])

        assert result.exit_code == 0
        assert "Stopped tracking" in result.output

    def test_stop_with_notes(self, runner: CliRunner, temp_dir: Path) -> None:
        """Test stop command with notes."""
        runner.invoke(cli, ["--data-dir", str(temp_dir), "start", "Test task"])

        result = runner.invoke(cli, ["--data-dir", str(temp_dir), "stop", "-n", "Completed"])

        assert result.exit_code == 0

    def test_stop_when_not_running(self, runner: CliRunner, temp_dir: Path) -> None:
        """Test stop command fails when nothing is running."""
        result = runner.invoke(cli, ["--data-dir", str(temp_dir), "stop"])

        assert result.exit_code == 1
        assert "Error" in result.output

    def test_status_command_not_tracking(self, runner: CliRunner, temp_dir: Path) -> None:
        """Test status command when not tracking."""
        result = runner.invoke(cli, ["--data-dir", str(temp_dir), "status"])

        assert result.exit_code == 0
        assert "No task currently being tracked" in result.output

    def test_status_command_tracking(self, runner: CliRunner, temp_dir: Path) -> None:
        """Test status command when tracking."""
        runner.invoke(cli, ["--data-dir", str(temp_dir), "start", "Test task"])

        result = runner.invoke(cli, ["--data-dir", str(temp_dir), "status"])

        assert result.exit_code == 0
        assert "Test task" in result.output

    def test_status_verbose(self, runner: CliRunner, temp_dir: Path) -> None:
        """Test status command with verbose flag."""
        runner.invoke(
            cli,
            [
                "--data-dir",
                str(temp_dir),
                "start",
                "Test task",
                "-p",
                "project",
                "-t",
                "tag1",
            ],
        )

        result = runner.invoke(cli, ["--data-dir", str(temp_dir), "status", "-v"])

        assert result.exit_code == 0
        assert "Entry ID:" in result.output

    def test_switch_command(self, runner: CliRunner, temp_dir: Path) -> None:
        """Test switch command."""
        runner.invoke(cli, ["--data-dir", str(temp_dir), "start", "First task"])

        result = runner.invoke(cli, ["--data-dir", str(temp_dir), "switch", "Second task"])

        assert result.exit_code == 0
        assert "Stopped: First task" in result.output
        assert "Started: Second task" in result.output

    def test_log_command(self, runner: CliRunner, temp_dir: Path) -> None:
        """Test log command."""
        # Add some entries
        runner.invoke(
            cli,
            [
                "--data-dir",
                str(temp_dir),
                "add",
                "Task 1",
                "--start",
                "09:00",
                "--end",
                "10:00",
            ],
        )

        result = runner.invoke(cli, ["--data-dir", str(temp_dir), "log"])

        assert result.exit_code == 0
        assert "Task 1" in result.output

    def test_log_with_filters(self, runner: CliRunner, temp_dir: Path) -> None:
        """Test log command with filters."""
        runner.invoke(
            cli,
            [
                "--data-dir",
                str(temp_dir),
                "add",
                "Task 1",
                "--start",
                "09:00",
                "--end",
                "10:00",
                "-p",
                "project-a",
            ],
        )

        result = runner.invoke(cli, ["--data-dir", str(temp_dir), "log", "-p", "project-a"])

        assert result.exit_code == 0
        assert "Task 1" in result.output

    def test_log_json_output(self, runner: CliRunner, temp_dir: Path) -> None:
        """Test log command with JSON output."""
        runner.invoke(
            cli,
            [
                "--data-dir",
                str(temp_dir),
                "add",
                "Task 1",
                "--start",
                "09:00",
                "--end",
                "10:00",
            ],
        )

        result = runner.invoke(cli, ["--data-dir", str(temp_dir), "log", "--json"])

        assert result.exit_code == 0
        assert "[" in result.output  # JSON array
        assert "task_name" in result.output

    def test_add_command(self, runner: CliRunner, temp_dir: Path) -> None:
        """Test add command."""
        result = runner.invoke(
            cli,
            [
                "--data-dir",
                str(temp_dir),
                "add",
                "Manual task",
                "--start",
                "09:00",
                "--end",
                "10:00",
            ],
        )

        assert result.exit_code == 0
        assert "Added manual entry" in result.output

    def test_add_with_full_datetime(self, runner: CliRunner, temp_dir: Path) -> None:
        """Test add command with full datetime format."""
        result = runner.invoke(
            cli,
            [
                "--data-dir",
                str(temp_dir),
                "add",
                "Task",
                "--start",
                "2025-11-16 09:00",
                "--end",
                "2025-11-16 10:00",
            ],
        )

        assert result.exit_code == 0

    def test_cancel_command(self, runner: CliRunner, temp_dir: Path) -> None:
        """Test cancel command."""
        runner.invoke(cli, ["--data-dir", str(temp_dir), "start", "Test task"])

        result = runner.invoke(cli, ["--data-dir", str(temp_dir), "cancel"])

        assert result.exit_code == 0
        assert "cancelled" in result.output.lower()

    def test_report_summary(self, runner: CliRunner, temp_dir: Path) -> None:
        """Test report summary command."""
        # Add some test data
        runner.invoke(
            cli,
            [
                "--data-dir",
                str(temp_dir),
                "add",
                "Task 1",
                "--start",
                "09:00",
                "--end",
                "10:00",
                "-p",
                "project-a",
            ],
        )

        result = runner.invoke(
            cli, ["--data-dir", str(temp_dir), "report", "summary", "--period", "today"]
        )

        assert result.exit_code == 0
        assert "Total Time" in result.output

    def test_report_timeline(self, runner: CliRunner, temp_dir: Path) -> None:
        """Test report timeline command."""
        runner.invoke(
            cli,
            [
                "--data-dir",
                str(temp_dir),
                "add",
                "Task 1",
                "--start",
                "09:00",
                "--end",
                "10:00",
            ],
        )

        result = runner.invoke(
            cli, ["--data-dir", str(temp_dir), "report", "timeline", "--period", "today"]
        )

        assert result.exit_code == 0
        assert "Timeline" in result.output

    def test_no_color_flag(self, runner: CliRunner, temp_dir: Path) -> None:
        """Test --no-color flag."""
        result = runner.invoke(
            cli,
            ["--no-color", "--data-dir", str(temp_dir), "status"],
        )

        assert result.exit_code == 0
