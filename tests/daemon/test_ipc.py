"""Tests for IPC communication."""

import json
import socket
import time

import pytest  # type: ignore[import-not-found]

from time_audit.daemon.ipc import IPCClient, IPCError, IPCServer
from time_audit.daemon.platform import Platform, get_platform


class TestIPCServer:
    """Test IPC server."""

    @pytest.fixture
    def socket_path(self, tmp_path):
        """Create temporary socket path."""
        if get_platform() == Platform.WINDOWS:
            pytest.skip("Windows named pipes require different testing approach")
        return tmp_path / "test.sock"

    def test_create_server(self, socket_path) -> None:
        """Test creating IPC server."""
        server = IPCServer(socket_path)
        assert server.socket_path == socket_path
        assert server.running is False

    def test_register_handler(self, socket_path) -> None:
        """Test registering request handler."""
        server = IPCServer(socket_path)

        def test_handler(params) -> None:
            return {"result": "ok"}

        server.register_handler("test", test_handler)
        assert "test" in server.handlers

    def test_start_and_stop_server(self, socket_path) -> None:
        """Test starting and stopping server."""
        server = IPCServer(socket_path)

        # Start server
        server.start()
        time.sleep(0.1)  # Give server time to start
        assert server.running is True
        assert socket_path.exists()

        # Stop server
        server.stop()
        time.sleep(0.1)
        assert server.running is False

    def test_server_handles_requests(self, socket_path) -> None:
        """Test server handles requests correctly."""
        server = IPCServer(socket_path)

        # Register handler
        def test_handler(params) -> None:
            return {"echo": params.get("message")}

        server.register_handler("echo", test_handler)

        # Start server
        server.start()
        time.sleep(0.1)

        try:
            # Connect and send request
            client_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            client_socket.connect(str(socket_path))

            request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "echo",
                "params": {"message": "hello"},
            }

            client_socket.sendall(json.dumps(request).encode("utf-8") + b"\n")

            # Receive response
            response_data = b""
            while b"\n" not in response_data:
                chunk = client_socket.recv(4096)
                if not chunk:
                    break
                response_data += chunk

            response = json.loads(response_data.decode("utf-8"))

            assert response["jsonrpc"] == "2.0"
            assert response["id"] == 1
            assert response["result"]["echo"] == "hello"

            client_socket.close()

        finally:
            server.stop()

    def test_server_handles_unknown_method(self, socket_path) -> None:
        """Test server returns error for unknown method."""
        server = IPCServer(socket_path)
        server.start()
        time.sleep(0.1)

        try:
            client_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            client_socket.connect(str(socket_path))

            request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "unknown",
                "params": {},
            }

            client_socket.sendall(json.dumps(request).encode("utf-8") + b"\n")

            # Receive response
            response_data = b""
            while b"\n" not in response_data:
                chunk = client_socket.recv(4096)
                if not chunk:
                    break
                response_data += chunk

            response = json.loads(response_data.decode("utf-8"))

            assert "error" in response
            assert response["error"]["code"] == -32601  # Method not found

            client_socket.close()

        finally:
            server.stop()


class TestIPCClient:
    """Test IPC client."""

    @pytest.fixture
    def socket_path(self, tmp_path):
        """Create temporary socket path."""
        if get_platform() == Platform.WINDOWS:
            pytest.skip("Windows named pipes require different testing approach")
        return tmp_path / "test.sock"

    @pytest.fixture
    def running_server(self, socket_path):
        """Create and start a test server."""
        server = IPCServer(socket_path)

        def ping_handler(params):
            return {"pong": True}

        def echo_handler(params):
            return {"echo": params.get("message")}

        server.register_handler("ping", ping_handler)
        server.register_handler("echo", echo_handler)

        server.start()
        time.sleep(0.1)

        yield server

        server.stop()

    def test_create_client(self, socket_path) -> None:
        """Test creating IPC client."""
        client = IPCClient(socket_path)
        assert client.socket_path == socket_path

    def test_client_call_success(self, socket_path, running_server) -> None:
        """Test successful client call."""
        client = IPCClient(socket_path)

        result = client.call("ping")

        assert result["pong"] is True

    def test_client_call_with_params(self, socket_path, running_server) -> None:
        """Test client call with parameters."""
        client = IPCClient(socket_path)

        result = client.call("echo", {"message": "test"})

        assert result["echo"] == "test"

    def test_client_call_unknown_method(self, socket_path, running_server) -> None:
        """Test client call with unknown method raises error."""
        client = IPCClient(socket_path)

        with pytest.raises(IPCError) as exc_info:
            client.call("unknown")

        assert "RPC error" in str(exc_info.value)

    def test_client_call_connection_refused(self, socket_path) -> None:
        """Test client call when server not running."""
        client = IPCClient(socket_path, timeout=1.0)

        with pytest.raises(IPCError) as exc_info:
            client.call("ping")

        assert "Failed to communicate" in str(exc_info.value)

    def test_is_daemon_running_true(self, socket_path, running_server) -> None:
        """Test is_daemon_running returns True when daemon is running."""
        client = IPCClient(socket_path)

        assert client.is_daemon_running() is True

    def test_is_daemon_running_false(self, socket_path) -> None:
        """Test is_daemon_running returns False when daemon is not running."""
        client = IPCClient(socket_path, timeout=0.5)

        assert client.is_daemon_running() is False


class TestIPCProtocol:
    """Test JSON-RPC protocol implementation."""

    @pytest.fixture
    def socket_path(self, tmp_path):
        """Create temporary socket path."""
        if get_platform() == Platform.WINDOWS:
            pytest.skip("Windows named pipes require different testing approach")
        return tmp_path / "test.sock"

    def test_json_rpc_request_format(self, socket_path) -> None:
        """Test JSON-RPC request format."""
        client = IPCClient(socket_path)
        client._request_id = 0

        # Build request
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "test",
            "params": {"key": "value"},
        }

        # Verify format
        assert request["jsonrpc"] == "2.0"
        assert "id" in request
        assert "method" in request
        assert "params" in request

    def test_json_rpc_success_response_format(self, socket_path) -> None:
        """Test JSON-RPC success response format."""
        server = IPCServer(socket_path)

        response = server._create_success_response(1, {"result": "ok"})

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "result" in response
        assert "error" not in response

    def test_json_rpc_error_response_format(self, socket_path) -> None:
        """Test JSON-RPC error response format."""
        server = IPCServer(socket_path)

        response = server._create_error_response(1, -32600, "Invalid Request")

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "error" in response
        assert "result" not in response
        assert response["error"]["code"] == -32600
        assert response["error"]["message"] == "Invalid Request"
