"""Tests for daemon state management."""

from time_audit.daemon.state import DaemonState, PIDFileManager, StateManager


class TestDaemonState:
    """Test DaemonState dataclass."""

    def test_create_daemon_state(self) -> None:
        """Test creating daemon state."""
        state = DaemonState(
            started_at="2025-11-16T10:00:00",
            pid=12345,
        )

        assert state.started_at == "2025-11-16T10:00:00"
        assert state.pid == 12345
        assert state.version == "0.3.0"
        assert state.tracking is False
        assert state.current_entry_id is None

    def test_daemon_state_to_dict(self) -> None:
        """Test converting state to dictionary."""
        state = DaemonState(
            started_at="2025-11-16T10:00:00",
            pid=12345,
        )

        state_dict = state.to_dict()
        assert isinstance(state_dict, dict)
        assert state_dict["started_at"] == "2025-11-16T10:00:00"
        assert state_dict["pid"] == 12345
        assert state_dict["version"] == "0.3.0"

    def test_daemon_state_from_dict(self) -> None:
        """Test creating state from dictionary."""
        data = {
            "started_at": "2025-11-16T10:00:00",
            "pid": 12345,
            "version": "0.3.0",
            "process_monitoring_enabled": True,
            "idle_monitoring_enabled": False,
            "notifications_enabled": True,
            "tracking": False,
            "current_entry_id": None,
            "current_task_name": None,
            "last_detected_process": None,
            "last_process_check": None,
            "is_idle": False,
            "idle_since": None,
            "last_activity_check": None,
            "process_checks_count": 0,
            "idle_checks_count": 0,
            "notifications_sent": 0,
        }

        state = DaemonState.from_dict(data)
        assert state.started_at == "2025-11-16T10:00:00"
        assert state.pid == 12345
        assert state.process_monitoring_enabled is True


class TestStateManager:
    """Test StateManager."""

    def test_initialize_state(self, tmp_path) -> None:
        """Test initializing daemon state."""
        state_file = tmp_path / "daemon.json"
        manager = StateManager(state_file)

        state = manager.initialize(12345)

        assert state is not None
        assert state.pid == 12345
        assert state.version == "0.3.0"

    def test_save_and_load_state(self, tmp_path) -> None:
        """Test saving and loading state."""
        state_file = tmp_path / "daemon.json"
        manager = StateManager(state_file)

        # Initialize and save
        state = manager.initialize(12345)
        manager.save()

        # Load in new manager
        manager2 = StateManager(state_file)
        loaded_state = manager2.load()

        assert loaded_state is not None
        assert loaded_state.pid == 12345
        assert loaded_state.version == state.version

    def test_update_state(self, tmp_path) -> None:
        """Test updating state fields."""
        state_file = tmp_path / "daemon.json"
        manager = StateManager(state_file)

        manager.initialize(12345)

        # Update fields
        manager.update(
            tracking=True,
            current_task_name="Test Task",
            process_checks_count=10,
        )

        # Get state
        state = manager.get()
        assert state.tracking is True
        assert state.current_task_name == "Test Task"
        assert state.process_checks_count == 10

    def test_get_dict(self, tmp_path) -> None:
        """Test getting state as dictionary."""
        state_file = tmp_path / "daemon.json"
        manager = StateManager(state_file)

        manager.initialize(12345)
        state_dict = manager.get_dict()

        assert isinstance(state_dict, dict)
        assert state_dict["pid"] == 12345

    def test_clear_state(self, tmp_path) -> None:
        """Test clearing state."""
        state_file = tmp_path / "daemon.json"
        manager = StateManager(state_file)

        manager.initialize(12345)
        assert state_file.exists()

        manager.clear()
        assert not state_file.exists()
        assert manager.get() is None

    def test_load_nonexistent_state(self, tmp_path) -> None:
        """Test loading state when file doesn't exist."""
        state_file = tmp_path / "nonexistent.json"
        manager = StateManager(state_file)

        state = manager.load()
        assert state is None

    def test_state_persistence_across_instances(self, tmp_path) -> None:
        """Test state persists across manager instances."""
        state_file = tmp_path / "daemon.json"

        # Create and update state
        manager1 = StateManager(state_file)
        manager1.initialize(12345)
        manager1.update(tracking=True, current_task_name="Test")

        # Load in new manager
        manager2 = StateManager(state_file)
        state = manager2.load()

        assert state.tracking is True
        assert state.current_task_name == "Test"


class TestPIDFileManager:
    """Test PIDFileManager."""

    def test_write_and_read_pid(self, tmp_path) -> None:
        """Test writing and reading PID."""
        pid_file = tmp_path / "daemon.pid"
        manager = PIDFileManager(pid_file)

        manager.write(12345)
        pid = manager.read()

        assert pid == 12345

    def test_read_nonexistent_pid(self, tmp_path) -> None:
        """Test reading PID when file doesn't exist."""
        pid_file = tmp_path / "nonexistent.pid"
        manager = PIDFileManager(pid_file)

        pid = manager.read()
        assert pid is None

    def test_read_invalid_pid(self, tmp_path) -> None:
        """Test reading invalid PID file."""
        pid_file = tmp_path / "daemon.pid"
        manager = PIDFileManager(pid_file)

        # Write invalid data
        with open(pid_file, "w") as f:
            f.write("invalid")

        pid = manager.read()
        assert pid is None

    def test_remove_pid_file(self, tmp_path) -> None:
        """Test removing PID file."""
        pid_file = tmp_path / "daemon.pid"
        manager = PIDFileManager(pid_file)

        manager.write(12345)
        assert pid_file.exists()

        manager.remove()
        assert not pid_file.exists()

    def test_remove_nonexistent_pid_file(self, tmp_path) -> None:
        """Test removing non-existent PID file doesn't error."""
        pid_file = tmp_path / "nonexistent.pid"
        manager = PIDFileManager(pid_file)

        manager.remove()  # Should not raise

    def test_is_running_with_existing_process(self, tmp_path) -> None:
        """Test is_running with current process."""
        import os

        pid_file = tmp_path / "daemon.pid"
        manager = PIDFileManager(pid_file)

        # Write current process PID
        current_pid = os.getpid()
        manager.write(current_pid)

        # Should detect as running
        assert manager.is_running() is True

    def test_is_running_with_nonexistent_pid_file(self, tmp_path) -> None:
        """Test is_running with no PID file."""
        pid_file = tmp_path / "nonexistent.pid"
        manager = PIDFileManager(pid_file)

        assert manager.is_running() is False
