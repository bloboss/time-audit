"""IPC (Inter-Process Communication) for daemon-client communication.

Uses JSON-RPC 2.0 protocol over Unix domain sockets (Linux/macOS) or named pipes (Windows).
"""

import json
import logging
import socket
import threading
from pathlib import Path
from typing import Any, Callable, Optional

from time_audit.daemon.platform import Platform, get_ipc_socket_path, get_platform

logger = logging.getLogger(__name__)


class IPCError(Exception):
    """IPC communication error."""

    pass


class IPCServer:
    """IPC server for handling client requests.

    Implements JSON-RPC 2.0 server over Unix sockets or named pipes.
    """

    def __init__(self, socket_path: Optional[Path] = None):
        """Initialize IPC server.

        Args:
            socket_path: Path to socket/named pipe (default: platform-specific)
        """
        self.socket_path = socket_path or get_ipc_socket_path()
        self.platform = get_platform()
        self.socket: Optional[socket.socket] = None
        self.running = False
        self.handlers: dict[str, Callable[..., Any]] = {}
        self._server_thread: Optional[threading.Thread] = None

    def register_handler(self, method: str, handler: Callable[..., Any]) -> None:
        """Register a handler for a JSON-RPC method.

        Args:
            method: Method name (e.g., 'status', 'start', 'stop')
            handler: Callable that handles the request
        """
        self.handlers[method] = handler
        logger.debug(f"Registered handler for method: {method}")

    def start(self) -> None:
        """Start the IPC server."""
        if self.running:
            logger.warning("IPC server already running")
            return

        # Clean up any existing socket
        if self.platform in (Platform.LINUX, Platform.MACOS):
            if self.socket_path.exists():
                self.socket_path.unlink()

        # Create socket
        if self.platform in (Platform.LINUX, Platform.MACOS):
            self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.socket.bind(str(self.socket_path))
            self.socket.listen(5)
            # Set socket permissions (owner only)
            self.socket_path.chmod(0o600)
        elif self.platform == Platform.WINDOWS:
            # Windows named pipes handled differently
            self._start_windows_server()
            return
        else:
            raise IPCError(f"Unsupported platform: {self.platform}")

        self.running = True
        self._server_thread = threading.Thread(target=self._accept_loop, daemon=True)
        self._server_thread.start()
        logger.info(f"IPC server started on {self.socket_path}")

    def _start_windows_server(self) -> None:
        """Start Windows named pipe server."""
        try:
            import win32file  # type: ignore[import-untyped]  # noqa: F401
            import win32pipe  # type: ignore[import-untyped]  # noqa: F401

            self.running = True
            self._server_thread = threading.Thread(target=self._accept_loop_windows, daemon=True)
            self._server_thread.start()
            logger.info(f"IPC server started on {self.socket_path}")
        except ImportError:
            raise IPCError("pywin32 is required for Windows daemon support")

    def _accept_loop(self) -> None:
        """Accept client connections (Unix)."""
        while self.running:
            try:
                if self.socket is None:
                    break

                self.socket.settimeout(1.0)  # Allow periodic checks of self.running
                try:
                    client_socket, _ = self.socket.accept()
                except socket.timeout:
                    continue

                # Handle client in separate thread
                client_thread = threading.Thread(
                    target=self._handle_client, args=(client_socket,), daemon=True
                )
                client_thread.start()
            except Exception as e:
                if self.running:  # Only log if not shutting down
                    logger.error(f"Error in accept loop: {e}")

    def _accept_loop_windows(self) -> None:
        """Accept client connections (Windows named pipes)."""
        import pywintypes  # type: ignore[import-untyped]
        import win32file  # type: ignore[import-untyped]
        import win32pipe  # type: ignore[import-untyped]

        while self.running:
            try:
                pipe = win32pipe.CreateNamedPipe(
                    str(self.socket_path),
                    win32pipe.PIPE_ACCESS_DUPLEX,
                    win32pipe.PIPE_TYPE_MESSAGE
                    | win32pipe.PIPE_READMODE_MESSAGE
                    | win32pipe.PIPE_WAIT,
                    win32pipe.PIPE_UNLIMITED_INSTANCES,
                    65536,
                    65536,
                    0,
                    None,
                )

                # Wait for client connection (with timeout)
                try:
                    win32pipe.ConnectNamedPipe(pipe, None)
                    # Handle client in separate thread
                    client_thread = threading.Thread(
                        target=self._handle_client_windows, args=(pipe,), daemon=True
                    )
                    client_thread.start()
                except pywintypes.error as e:
                    if e.args[0] != 232:  # ERROR_NO_DATA (client disconnected)
                        logger.error(f"Error accepting connection: {e}")
                    win32file.CloseHandle(pipe)
            except Exception as e:
                if self.running:
                    logger.error(f"Error in Windows accept loop: {e}")

    def _handle_client(self, client_socket: socket.socket) -> None:
        """Handle a client connection (Unix).

        Args:
            client_socket: Client socket
        """
        try:
            # Receive request
            data = b""
            while True:
                chunk = client_socket.recv(4096)
                if not chunk:
                    break
                data += chunk
                if b"\n" in chunk:  # Simple message delimiter
                    break

            if not data:
                return

            # Parse JSON-RPC request
            try:
                request = json.loads(data.decode("utf-8"))
            except json.JSONDecodeError as e:
                error_response = self._create_error_response(None, -32700, str(e))
                client_socket.sendall(json.dumps(error_response).encode("utf-8"))
                return

            # Process request
            response = self._process_request(request)

            # Send response
            response_data = json.dumps(response).encode("utf-8") + b"\n"
            client_socket.sendall(response_data)

        except Exception as e:
            logger.error(f"Error handling client: {e}")
        finally:
            client_socket.close()

    def _handle_client_windows(self, pipe: Any) -> None:
        """Handle a client connection (Windows named pipe).

        Args:
            pipe: Named pipe handle
        """
        import win32file

        try:
            # Read request
            result, data = win32file.ReadFile(pipe, 65536)

            if not data:
                return

            # Parse JSON-RPC request
            try:
                request = json.loads(data.decode("utf-8"))
            except json.JSONDecodeError as e:
                error_response = self._create_error_response(None, -32700, str(e))
                response_data = json.dumps(error_response).encode("utf-8")
                win32file.WriteFile(pipe, response_data)
                return

            # Process request
            response = self._process_request(request)

            # Send response
            response_data = json.dumps(response).encode("utf-8")
            win32file.WriteFile(pipe, response_data)

        except Exception as e:
            logger.error(f"Error handling Windows client: {e}")
        finally:
            win32file.CloseHandle(pipe)

    def _process_request(self, request: dict[str, Any]) -> dict[str, Any]:
        """Process a JSON-RPC request.

        Args:
            request: JSON-RPC request dictionary

        Returns:
            JSON-RPC response dictionary
        """
        # Validate JSON-RPC request
        if not isinstance(request, dict):
            return self._create_error_response(None, -32600, "Invalid Request")

        request_id = request.get("id")
        method = request.get("method")
        params = request.get("params", {})

        if not method or not isinstance(method, str):
            return self._create_error_response(request_id, -32600, "Invalid Request")

        # Find handler
        handler = self.handlers.get(method)
        if not handler:
            return self._create_error_response(request_id, -32601, f"Method not found: {method}")

        # Call handler
        try:
            result = handler(params)
            return self._create_success_response(request_id, result)
        except Exception as e:
            logger.error(f"Error in handler for {method}: {e}")
            return self._create_error_response(request_id, -32603, str(e))

    def _create_success_response(self, request_id: Optional[Any], result: Any) -> dict[str, Any]:
        """Create a JSON-RPC success response."""
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    def _create_error_response(
        self, request_id: Optional[Any], code: int, message: str
    ) -> dict[str, Any]:
        """Create a JSON-RPC error response."""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": code, "message": message},
        }

    def stop(self) -> None:
        """Stop the IPC server."""
        if not self.running:
            return

        logger.info("Stopping IPC server...")
        self.running = False

        # Close socket
        if self.socket:
            self.socket.close()
            self.socket = None

        # Wait for server thread
        if self._server_thread:
            self._server_thread.join(timeout=2.0)

        # Clean up socket file
        if self.platform in (Platform.LINUX, Platform.MACOS):
            if self.socket_path.exists():
                self.socket_path.unlink()

        logger.info("IPC server stopped")


class IPCClient:
    """IPC client for communicating with daemon.

    Implements JSON-RPC 2.0 client over Unix sockets or named pipes.
    """

    def __init__(self, socket_path: Optional[Path] = None, timeout: float = 5.0):
        """Initialize IPC client.

        Args:
            socket_path: Path to socket/named pipe (default: platform-specific)
            timeout: Connection timeout in seconds
        """
        self.socket_path = socket_path or get_ipc_socket_path()
        self.timeout = timeout
        self.platform = get_platform()
        self._request_id = 0

    def call(self, method: str, params: Optional[dict[str, Any]] = None) -> Any:
        """Call a remote method.

        Args:
            method: Method name
            params: Method parameters

        Returns:
            Method result

        Raises:
            IPCError: If communication fails or method returns error
        """
        self._request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
            "params": params or {},
        }

        try:
            response = self._send_request(request)
        except Exception as e:
            raise IPCError(f"Failed to communicate with daemon: {e}")

        # Check for error response
        if "error" in response:
            error = response["error"]
            raise IPCError(f"RPC error {error.get('code')}: {error.get('message')}")

        return response.get("result")

    def _send_request(self, request: dict[str, Any]) -> dict[str, Any]:
        """Send request and receive response.

        Args:
            request: JSON-RPC request

        Returns:
            JSON-RPC response

        Raises:
            IPCError: If communication fails
        """
        if self.platform in (Platform.LINUX, Platform.MACOS):
            return self._send_request_unix(request)
        elif self.platform == Platform.WINDOWS:
            return self._send_request_windows(request)
        else:
            raise IPCError(f"Unsupported platform: {self.platform}")

    def _send_request_unix(self, request: dict[str, Any]) -> dict[str, Any]:
        """Send request via Unix socket.

        Args:
            request: JSON-RPC request

        Returns:
            JSON-RPC response
        """
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)

        try:
            sock.connect(str(self.socket_path))

            # Send request
            request_data = json.dumps(request).encode("utf-8") + b"\n"
            sock.sendall(request_data)

            # Receive response
            response_data = b""
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response_data += chunk
                if b"\n" in chunk:
                    break

            response = json.loads(response_data.decode("utf-8"))
            return response  # type: ignore[no-any-return]

        finally:
            sock.close()

    def _send_request_windows(self, request: dict[str, Any]) -> dict[str, Any]:
        """Send request via Windows named pipe.

        Args:
            request: JSON-RPC request

        Returns:
            JSON-RPC response
        """
        try:
            import win32file
            import win32pipe  # noqa: F401
        except ImportError:
            raise IPCError("pywin32 is required for Windows daemon support")

        try:
            # Connect to named pipe
            handle = win32file.CreateFile(
                str(self.socket_path),
                win32file.GENERIC_READ | win32file.GENERIC_WRITE,
                0,
                None,
                win32file.OPEN_EXISTING,
                0,
                None,
            )

            # Send request
            request_data = json.dumps(request).encode("utf-8")
            win32file.WriteFile(handle, request_data)

            # Receive response
            result, response_data = win32file.ReadFile(handle, 65536)
            response = json.loads(response_data.decode("utf-8"))

            return response  # type: ignore[no-any-return]

        finally:
            if handle:
                win32file.CloseHandle(handle)

    def is_daemon_running(self) -> bool:
        """Check if daemon is running.

        Returns:
            True if daemon is accessible, False otherwise
        """
        try:
            self.call("ping")
            return True
        except IPCError:
            return False
