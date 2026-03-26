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

"""
This script provides functionality for handling events from the container via a
TCP socket.
"""

import logging
import os
import socket
from datetime import datetime, timezone
from threading import Event, Thread


class SocketCancelEvent:
    """
    A wrapper around threading.Event that also unblocks a listening socket
    by shutting it down when set() is called.
    """

    def __init__(self, event: Event, server_socket: socket.socket):
        self._event = event
        self._socket = server_socket

    def is_set(self) -> bool:
        return self._event.is_set()

    def set(self) -> None:
        self._event.set()
        # Wake up the blocking accept() by shutting down the socket
        try:
            self._socket.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass


def handle_entrypoint_end_time_ms(value: str) -> None:
    """
    Parses the entrypoint_end_time_ms value into a proper python datetime object
    and calculates latency from DEVKIT_START_TIME_MS.
    """
    try:
        ts_end = int(value.strip())
        if ts_end < 0:
            raise ValueError("Timestamp cannot be negative.")

        # Convert milliseconds to a UTC datetime object
        dt_end = datetime.fromtimestamp(ts_end / 1000, timezone.utc)
        logging.info("Successfully parsed entrypoint end time: %s", dt_end.isoformat())

        # Access the start time from the environment
        start_time_env = os.environ.get("DEVKIT_START_TIME_MS")
        if start_time_env:
            try:
                ts_start = int(start_time_env)
                latency_ms = ts_end - ts_start
                logging.info(
                    "Calculated latency until entrypoint end: %d ms", latency_ms
                )

            except ValueError:
                logging.warning(
                    "DEVKIT_START_TIME_MS is not a valid integer: %s", start_time_env
                )
        else:
            logging.warning("DEVKIT_START_TIME_MS environment variable not found.")

    except ValueError as e:
        logging.error("Failed to parse entrypoint_end_time_ms: %s", e)


def process_container_event(data: bytes) -> None:
    """
    Decodes and dispatches a container event based on its name.
    """
    decoded_data = data.decode(errors="replace").strip()
    logging.info("Container event data: %s", decoded_data)

    # Parse the event name and value
    if ":" in decoded_data:
        event_name, event_value = decoded_data.split(":", 1)
        if event_name == "entrypoint_end_time_ms":
            handle_entrypoint_end_time_ms(event_value)
        else:
            logging.warning("Unknown container event: %s", event_name)
    else:
        logging.warning("Malformed container event: %s", decoded_data)


def container_event_listener(
    server_socket: socket.socket, cancel_event: SocketCancelEvent
) -> None:
    """
    Listens on a TCP socket for events from the container.
    """
    try:
        server_socket.listen(1)
        logging.info(
            "Container event handler listening on TCP %s:%d",
            *server_socket.getsockname(),
        )

        while not cancel_event.is_set():
            try:
                conn, _ = server_socket.accept()
                with conn:
                    data = conn.recv(1024)
                    if not data:
                        continue

                    logging.info("Received event from container")
                    process_container_event(data)
            except OSError as e:
                # If the socket was shut down by the cancel event, exit gracefully.
                if cancel_event.is_set():
                    break
                logging.error("Error in container event listener: %s", e)
                break
            except Exception as e:
                if not cancel_event.is_set():
                    logging.error("Unexpected error in container event listener: %s", e)
                break
    except Exception as e:
        logging.error("Failed in container event listener: %s", e)
    finally:
        server_socket.close()


def start_container_event_handler() -> tuple[Thread, SocketCancelEvent, int]:
    """
    Starts the container event handler in a background daemon thread on a random TCP port.
    Returns the thread, the event used to stop it, and the port number.
    """
    base_event = Event()

    # Create the socket in the main thread to reliably get the bound port
    # before returning, avoiding race conditions.
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]

    cancel_event = SocketCancelEvent(base_event, s)

    thread = Thread(
        target=container_event_listener,
        args=(s, cancel_event),
        name=f"ContainerEventHandler-{port}",
        daemon=True,
    )
    thread.start()

    return thread, cancel_event, port
