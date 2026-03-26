#!/usr/bin/env python3
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Test cases for the container_event_handler script."""

import os
import socket
import unittest
from threading import Event
from unittest.mock import MagicMock, patch

from scripts import container_event_handler


class TestSocketCancelEvent(unittest.TestCase):
    """Tests for SocketCancelEvent class."""

    def test_set_and_is_set(self) -> None:
        """Test that set() sets the event and shuts down the socket."""
        mock_event = MagicMock(spec=Event)
        mock_socket = MagicMock(spec=socket.socket)
        cancel_event = container_event_handler.SocketCancelEvent(
            mock_event, mock_socket
        )

        cancel_event.set()
        mock_event.set.assert_called_once()
        mock_socket.shutdown.assert_called_once_with(socket.SHUT_RDWR)

        mock_event.is_set.return_value = True
        self.assertTrue(cancel_event.is_set())

    def test_set_socket_error(self) -> None:
        """Test that set() handles OSError from socket.shutdown."""
        mock_event = MagicMock(spec=Event)
        mock_socket = MagicMock(spec=socket.socket)
        mock_socket.shutdown.side_effect = OSError("Socket already closed")
        cancel_event = container_event_handler.SocketCancelEvent(
            mock_event, mock_socket
        )

        # Should not raise exception
        cancel_event.set()
        mock_event.set.assert_called_once()
        mock_socket.shutdown.assert_called_once()


class TestContainerEventHandler(unittest.TestCase):
    """Tests for container_event_handler functions."""

    @patch("scripts.container_event_handler.logging")
    def test_handle_entrypoint_end_time_ms_success(
        self, mock_logging: MagicMock
    ) -> None:
        """Test successful parsing of entrypoint_end_time_ms."""
        with patch.dict(os.environ, {"DEVKIT_START_TIME_MS": "1000"}):
            container_event_handler.handle_entrypoint_end_time_ms("2000")
            mock_logging.info.assert_any_call(
                "Calculated latency until entrypoint end: %d ms", 1000
            )

    @patch("scripts.container_event_handler.logging")
    def test_handle_entrypoint_end_time_ms_invalid_value(
        self, mock_logging: MagicMock
    ) -> None:
        """Test handle_entrypoint_end_time_ms with invalid value."""
        container_event_handler.handle_entrypoint_end_time_ms("not_an_int")
        mock_logging.error.assert_called()

    @patch("scripts.container_event_handler.logging")
    def test_handle_entrypoint_end_time_ms_negative_value(
        self, mock_logging: MagicMock
    ) -> None:
        """Test handle_entrypoint_end_time_ms with negative value."""
        container_event_handler.handle_entrypoint_end_time_ms("-1000")
        mock_logging.error.assert_called()

    @patch("scripts.container_event_handler.logging")
    def test_handle_entrypoint_end_time_ms_missing_env(
        self, mock_logging: MagicMock
    ) -> None:
        """Test handle_entrypoint_end_time_ms with missing DEVKIT_START_TIME_MS."""
        with patch.dict(os.environ, {}, clear=True):
            container_event_handler.handle_entrypoint_end_time_ms("2000")
            mock_logging.warning.assert_any_call(
                "DEVKIT_START_TIME_MS environment variable not found."
            )

    @patch("scripts.container_event_handler.logging")
    def test_handle_entrypoint_end_time_ms_invalid_env(
        self, mock_logging: MagicMock
    ) -> None:
        """Test handle_entrypoint_end_time_ms with invalid DEVKIT_START_TIME_MS."""
        with patch.dict(os.environ, {"DEVKIT_START_TIME_MS": "invalid"}):
            container_event_handler.handle_entrypoint_end_time_ms("2000")
            mock_logging.warning.assert_any_call(
                "DEVKIT_START_TIME_MS is not a valid integer: %s", "invalid"
            )

    @patch("scripts.container_event_handler.handle_entrypoint_end_time_ms")
    @patch("scripts.container_event_handler.logging")
    def test_process_container_event_success(
        self, unused_logging: MagicMock, mock_handler: MagicMock
    ) -> None:
        """Test process_container_event with valid event."""
        del unused_logging
        data = b"entrypoint_end_time_ms:12345"
        container_event_handler.process_container_event(data)
        mock_handler.assert_called_once_with("12345")

    @patch("scripts.container_event_handler.logging")
    def test_process_container_event_unknown(self, mock_logging: MagicMock) -> None:
        """Test process_container_event with unknown event."""
        data = b"unknown_event:value"
        container_event_handler.process_container_event(data)
        mock_logging.warning.assert_called_with(
            "Unknown container event: %s", "unknown_event"
        )

    @patch("scripts.container_event_handler.logging")
    def test_process_container_event_malformed(self, mock_logging: MagicMock) -> None:
        """Test process_container_event with malformed data."""
        data = b"malformed_data"
        container_event_handler.process_container_event(data)
        mock_logging.warning.assert_called_with(
            "Malformed container event: %s", "malformed_data"
        )

    @patch("scripts.container_event_handler.process_container_event")
    @patch("scripts.container_event_handler.logging")
    def test_container_event_listener_success(
        self, unused_logging: MagicMock, mock_process: MagicMock
    ) -> None:
        """Test container_event_listener successful loop."""
        del unused_logging
        mock_socket = MagicMock(spec=socket.socket)
        mock_conn = MagicMock(spec=socket.socket)
        mock_socket.accept.return_value = (mock_conn, ("127.0.0.1", 12345))
        mock_conn.recv.return_value = b"event:data"

        mock_cancel = MagicMock()
        # Set is_set() to False then True to exit the loop
        mock_cancel.is_set.side_effect = [False, True]

        container_event_handler.container_event_listener(mock_socket, mock_cancel)

        mock_socket.listen.assert_called_once_with(1)
        mock_process.assert_called_once_with(b"event:data")
        mock_socket.close.assert_called_once()

    @patch("scripts.container_event_handler.logging")
    def test_container_event_listener_os_error_cancel(
        self, mock_logging: MagicMock
    ) -> None:
        """Test container_event_listener handles OSError when cancelled."""
        mock_socket = MagicMock(spec=socket.socket)
        mock_socket.accept.side_effect = OSError("Socket closed")

        mock_cancel = MagicMock()
        # First call in while condition: False
        # Second call in except block: True
        mock_cancel.is_set.side_effect = [False, True]

        container_event_handler.container_event_listener(mock_socket, mock_cancel)

        # Should break loop and not log error
        mock_logging.error.assert_not_called()

    @patch("scripts.container_event_handler.logging")
    def test_container_event_listener_os_error_real(
        self, mock_logging: MagicMock
    ) -> None:
        """Test container_event_listener handles real OSError."""
        mock_socket = MagicMock(spec=socket.socket)
        mock_socket.accept.side_effect = OSError("Real error")

        mock_cancel = MagicMock()
        mock_cancel.is_set.return_value = False

        container_event_handler.container_event_listener(mock_socket, mock_cancel)

        mock_logging.error.assert_called()

    @patch("scripts.container_event_handler.process_container_event")
    @patch("scripts.container_event_handler.logging")
    def test_container_event_listener_empty_data(
        self, unused_logging: MagicMock, mock_process: MagicMock
    ) -> None:
        """Test container_event_listener with empty data from recv."""
        del unused_logging
        mock_socket = MagicMock(spec=socket.socket)
        mock_conn = MagicMock(spec=socket.socket)
        mock_socket.accept.return_value = (mock_conn, ("127.0.0.1", 12345))
        # First call returns empty data, second call is_set() becomes true
        mock_conn.recv.return_value = b""

        mock_cancel = MagicMock()
        mock_cancel.is_set.side_effect = [False, True]

        container_event_handler.container_event_listener(mock_socket, mock_cancel)

        mock_process.assert_not_called()

    @patch("scripts.container_event_handler.logging")
    def test_container_event_listener_unexpected_exception_in_loop(
        self, mock_logging: MagicMock
    ) -> None:
        """Test container_event_listener with unexpected exception in loop."""
        mock_socket = MagicMock(spec=socket.socket)
        mock_socket.accept.side_effect = Exception("Unexpected")

        mock_cancel = MagicMock()
        mock_cancel.is_set.return_value = False

        container_event_handler.container_event_listener(mock_socket, mock_cancel)

        mock_logging.error.assert_called_with(
            "Unexpected error in container event listener: %s",
            mock_socket.accept.side_effect,
        )

    @patch("scripts.container_event_handler.logging")
    def test_container_event_listener_exception_on_listen(
        self, mock_logging: MagicMock
    ) -> None:
        """Test container_event_listener with exception on listen."""
        mock_socket = MagicMock(spec=socket.socket)
        mock_socket.listen.side_effect = Exception("Listen failed")

        mock_cancel = MagicMock()

        container_event_handler.container_event_listener(mock_socket, mock_cancel)

        mock_logging.error.assert_called_with(
            "Failed in container event listener: %s", mock_socket.listen.side_effect
        )

    @patch("scripts.container_event_handler.Thread")
    @patch("scripts.container_event_handler.socket.socket")
    def test_start_container_event_handler(
        self, mock_socket_class: MagicMock, mock_thread_class: MagicMock
    ) -> None:
        """Test start_container_event_handler."""
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket
        mock_socket.getsockname.return_value = ("127.0.0.1", 12345)

        unused_thread, unused_cancel_event, port = (
            container_event_handler.start_container_event_handler()
        )
        del unused_thread, unused_cancel_event

        self.assertEqual(port, 12345)
        mock_socket.bind.assert_called_once_with(("127.0.0.1", 0))
        mock_thread_class.assert_called_once()
        mock_thread_class.return_value.start.assert_called_once()


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
