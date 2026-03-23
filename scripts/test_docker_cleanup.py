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

"""Test cases for the docker_cleanup script."""

import subprocess
import unittest
from pathlib import Path
from threading import Event, Thread
from unittest.mock import patch, MagicMock
from scripts import docker_cleanup


class TestDockerCleanup(unittest.TestCase):
    """Tests for docker_cleanup script."""

    @patch("scripts.docker_cleanup.cleanup_images_batch")
    @patch("scripts.docker_cleanup.get_images_to_cleanup")
    def test_start_background_cleanup(
        self, mock_get_to_cleanup: MagicMock, mock_cleanup: MagicMock
    ) -> None:
        """Test starting background cleanup."""
        del mock_get_to_cleanup, mock_cleanup  # Unused
        config_path = Path("devkit.json")
        search_paths = [Path("images")]
        thread, cancel_event = docker_cleanup.start_background_cleanup(
            config_path, search_paths
        )
        self.assertIsInstance(thread, Thread)
        self.assertIsInstance(cancel_event, Event)
        self.assertTrue(thread.is_alive())
        self.assertEqual(thread.name, "DockerCleanupThread")

        # Cleanup
        cancel_event.set()
        thread.join(timeout=1.0)
        self.assertFalse(thread.is_alive())

    def test_cleanup_images_exit_on_initial_wait(self) -> None:
        """Test cleanup_images exits if initial wait returns True (cancelled)."""
        cancel_event = MagicMock(spec=Event)
        cancel_event.wait.return_value = True

        with patch("scripts.docker_cleanup.get_images_to_cleanup") as mock_get:
            docker_cleanup.cleanup_images(cancel_event, Path("c"), [Path("s")])
            mock_get.assert_not_called()
            cancel_event.wait.assert_called_once_with(
                docker_cleanup.INITIAL_CLEANUP_DELAY_SECONDS
            )

    @patch("scripts.docker_cleanup.cleanup_images_batch")
    @patch("scripts.docker_cleanup.get_images_to_cleanup")
    def test_cleanup_images_loop_behavior(
        self,
        mock_get_to_cleanup: MagicMock,
        mock_cleanup: MagicMock,
    ) -> None:
        """Test cleanup_images loop behavior: processes in batches."""
        # 12 images to clean up -> 3 batches (4, 4, 4)
        mock_get_to_cleanup.return_value = [f"img{i}" for i in range(12)]

        cancel_event = MagicMock(spec=Event)
        # initial wait -> False
        # loop 1 interval -> False
        # loop 2 interval -> False
        # loop 3 interval -> True (exit)
        cancel_event.wait.side_effect = [False, False, False, True]

        docker_cleanup.cleanup_images(cancel_event, Path("c"), [Path("s")])

        mock_get_to_cleanup.assert_called_once_with(Path("c"), [Path("s")], 7)

        self.assertEqual(mock_cleanup.call_count, 3)
        mock_cleanup.assert_any_call(cancel_event, ["img0", "img1", "img2", "img3"])
        mock_cleanup.assert_any_call(cancel_event, ["img4", "img5", "img6", "img7"])
        mock_cleanup.assert_any_call(cancel_event, ["img8", "img9", "img10", "img11"])

    @patch("scripts.docker_cleanup.cleanup_images_batch")
    @patch("scripts.docker_cleanup.get_images_to_cleanup")
    def test_cleanup_images_cancel_between_batches(
        self,
        mock_get_to_cleanup: MagicMock,
        mock_cleanup: MagicMock,
    ) -> None:
        """Test cleanup_images exits if cancel_event is set between batches."""
        # 6 images -> 2 batches
        mock_get_to_cleanup.return_value = [f"img{i}" for i in range(6)]

        cancel_event = MagicMock(spec=Event)
        # initial wait -> False, first interval wait -> True (exit)
        cancel_event.wait.side_effect = [False, True]

        docker_cleanup.cleanup_images(cancel_event, Path("c"), [Path("s")])

        self.assertEqual(mock_cleanup.call_count, 1)

    @patch("scripts.docker_cleanup.cleanup_images_batch")
    @patch("scripts.docker_cleanup.get_images_to_cleanup")
    def test_cleanup_images_exit_on_interval_wait(
        self,
        mock_get_to_cleanup: MagicMock,
        mock_cleanup: MagicMock,
    ) -> None:
        """Test cleanup_images exits if interval wait returns True (cancelled)."""
        mock_get_to_cleanup.return_value = [
            "img1",
            "img2",
            "img3",
            "img4",
            "img5",
            "img6",
        ]

        cancel_event = MagicMock(spec=Event)
        # initial wait -> False, first interval wait -> True (exit)
        cancel_event.wait.side_effect = [False, True]
        cancel_event.is_set.return_value = False

        docker_cleanup.cleanup_images(cancel_event, Path("c"), [Path("s")])

        mock_cleanup.assert_called_once()

    @patch("scripts.docker_cleanup.filter_allowed_images")
    @patch("scripts.docker_cleanup.get_ignored_images")
    @patch("scripts.docker_cleanup.get_images")
    @patch("scripts.docker_cleanup.get_image_prefix")
    def test_get_images_to_cleanup_success(
        self,
        mock_prefix: MagicMock,
        mock_get_imgs: MagicMock,
        mock_ignored: MagicMock,
        mock_filter: MagicMock,
    ) -> None:
        """Test get_images_to_cleanup successful flow."""
        mock_prefix.return_value = "prefix/devkit"
        mock_get_imgs.return_value = [
            "prefix/devkit/vscode-ide:amd64-"
            "c79258f05d8fdf75d18f7485240f25"
            "b9579a4ea68005d7865e71b7b9dbf13548",
            "prefix/devkit/other:tag",
            "prefix/devkit/vscode-server:ignored",
        ]
        mock_filter.return_value = [
            "prefix/devkit/vscode-ide:amd64-"
            "c79258f05d8fdf75d18f7485240f25"
            "b9579a4ea68005d7865e71b7b9dbf13548"
        ]
        mock_ignored.return_value = ["prefix/devkit/vscode-server:ignored"]

        res = docker_cleanup.get_images_to_cleanup(Path("c"), [Path("s")], 7)

        self.assertEqual(
            res,
            [
                "prefix/devkit/vscode-ide:amd64-"
                "c79258f05d8fdf75d18f7485240f25"
                "b9579a4ea68005d7865e71b7b9dbf13548"
            ],
        )
        mock_prefix.assert_called_once_with(Path("c"))
        mock_get_imgs.assert_called_once_with("prefix/devkit", 7)
        mock_filter.assert_called_once_with(mock_get_imgs.return_value)
        mock_ignored.assert_called_once_with(Path("c"), [Path("s")])

    @patch("scripts.docker_cleanup.filter_allowed_images")
    @patch("scripts.docker_cleanup.get_images")
    @patch("scripts.docker_cleanup.get_image_prefix")
    @patch("scripts.docker_cleanup.logging.info")
    def test_get_images_to_cleanup_no_allowed_images(
        self,
        mock_logging_info: MagicMock,
        mock_prefix: MagicMock,
        mock_get_imgs: MagicMock,
        mock_filter: MagicMock,
    ) -> None:
        """Test get_images_to_cleanup when no allowed images found."""
        mock_prefix.return_value = "p"
        mock_get_imgs.return_value = ["p/other:tag"]
        mock_filter.return_value = []
        res = docker_cleanup.get_images_to_cleanup(Path("c"), [Path("s")], 7)
        self.assertEqual(res, [])
        mock_filter.assert_called_once_with(mock_get_imgs.return_value)
        mock_logging_info.assert_any_call("No allowed images found for cleanup.")

    @patch("scripts.docker_cleanup.filter_allowed_images")
    @patch("scripts.docker_cleanup.get_images")
    @patch("scripts.docker_cleanup.get_image_prefix")
    @patch("scripts.docker_cleanup.logging.info")
    def test_get_images_to_cleanup_no_images(
        self,
        mock_logging_info: MagicMock,
        mock_prefix: MagicMock,
        mock_get_imgs: MagicMock,
        mock_filter: MagicMock,
    ) -> None:
        """Test get_images_to_cleanup when no images found."""
        mock_prefix.return_value = "p"
        mock_get_imgs.return_value = []
        res = docker_cleanup.get_images_to_cleanup(Path("c"), [Path("s")], 7)
        self.assertEqual(res, [])
        mock_filter.assert_not_called()
        mock_logging_info.assert_any_call("No images found for cleanup.")

    @patch("scripts.docker_cleanup.filter_allowed_images")
    @patch("scripts.docker_cleanup.get_ignored_images")
    @patch("scripts.docker_cleanup.get_images")
    @patch("scripts.docker_cleanup.get_image_prefix")
    @patch("scripts.docker_cleanup.logging.info")
    def test_get_images_to_cleanup_all_ignored(
        self,
        mock_logging_info: MagicMock,
        mock_prefix: MagicMock,
        mock_get_imgs: MagicMock,
        mock_ignored: MagicMock,
        mock_filter: MagicMock,
    ) -> None:
        """Test get_images_to_cleanup when all images are ignored."""
        mock_prefix.return_value = "p/devkit"
        mock_get_imgs.return_value = [
            "p/devkit/vscode-ide:amd64-"
            "c79258f05d8fdf75d18f7485240f25"
            "b9579a4ea68005d7865e71b7b9dbf13548"
        ]
        mock_filter.return_value = [
            "p/devkit/vscode-ide:amd64-"
            "c79258f05d8fdf75d18f7485240f25"
            "b9579a4ea68005d7865e71b7b9dbf13548"
        ]
        mock_ignored.return_value = [
            "p/devkit/vscode-ide:amd64-"
            "c79258f05d8fdf75d18f7485240f25"
            "b9579a4ea68005d7865e71b7b9dbf13548"
        ]
        res = docker_cleanup.get_images_to_cleanup(Path("c"), [Path("s")], 7)
        self.assertEqual(res, [])
        mock_filter.assert_called_once_with(mock_get_imgs.return_value)
        mock_logging_info.assert_any_call(
            "All found images are in the ignore list. Nothing to clean up."
        )

    def test_filter_allowed_images(self) -> None:
        """
        Test filter_allowed_images filters out non-allowed
        and improperly formatted images.
        """
        images = [
            "devkit/tool-env:amd64-"
            "c79258f05d8fdf75d18f7485240f25"
            "b9579a4ea68005d7865e71b7b9dbf13548",  # Valid
            "registry.example.com/project/repository/devkit/tool-env:amd64-"
            "c79258f05d8fdf75d18f7485240f25"
            "b9579a4ea68005d7865e71b7b9dbf13548",  # Valid full path with devkit
            "registry.example.com/project/repository/devkit/demo/tool-env:amd64-"
            "c79258f05d8fdf75d18f7485240f25"
            "b9579a4ea68005d7865e71b7b9dbf13548",  # Valid full path with devkit and demo
            "tool-env:arm64-"
            "c79258f05d8fdf75d18f7485240f25"
            "b9579a4ea68005d7865e71b7b9dbf13548",  # Invalid, no namespace
            "other/tool-env:amd64-"
            "c79258f05d8fdf75d18f7485240f25"
            "b9579a4ea68005d7865e71b7b9dbf13548",  # Invalid, no devkit in namespace
            "devkit/unknown-env:amd64-"
            "c79258f05d8fdf75d18f7485240f25"
            "b9579a4ea68005d7865e71b7b9dbf13548",  # Invalid name
            "devkit/tool-env:amd64-c792",  # Invalid hash length
            "devkit/tool-env:amd64-"
            "c79258f05d8fdf75d18f7485240f25"
            "b9579a4ea68005d7865e71b7b9dbf1354g",  # Invalid hash chars
            "devkit/tool-env:tag",  # Invalid tag format
            "tool-env",  # No tag
        ]

        expected = [
            "devkit/tool-env:amd64-"
            "c79258f05d8fdf75d18f7485240f25"
            "b9579a4ea68005d7865e71b7b9dbf13548",
            "registry.example.com/project/repository/devkit/tool-env:amd64-"
            "c79258f05d8fdf75d18f7485240f25"
            "b9579a4ea68005d7865e71b7b9dbf13548",
            "registry.example.com/project/repository/devkit/demo/tool-env:amd64-"
            "c79258f05d8fdf75d18f7485240f25"
            "b9579a4ea68005d7865e71b7b9dbf13548",
        ]

        filtered = docker_cleanup.filter_allowed_images(images)
        self.assertEqual(filtered, expected)

    @patch("scripts.docker_cleanup.get_all_docker_image_tags")
    def test_get_ignored_images_success(self, mock_get_all: MagicMock) -> None:
        """Test get_ignored_images successfully returns tags."""
        mock_get_all.return_value = ["t1", "t2"]
        tags = docker_cleanup.get_ignored_images(Path("c"), [Path("s")])
        self.assertEqual(tags, ["t1", "t2"])

    @patch("scripts.docker_cleanup.get_all_docker_image_tags")
    @patch("scripts.docker_cleanup.logging.warning")
    def test_get_ignored_images_exception(
        self, mock_warning: MagicMock, mock_get_all: MagicMock
    ) -> None:
        """Test get_ignored_images handles exception."""
        mock_get_all.side_effect = Exception("error")
        tags = docker_cleanup.get_ignored_images(Path("c"), [Path("s")])
        self.assertEqual(tags, [])
        mock_warning.assert_called_once()

    @patch("scripts.docker_cleanup.subprocess.run")
    def test_get_images_success(self, mock_run: MagicMock) -> None:
        """Test get_images successfully lists images."""
        mock_run.return_value = MagicMock(
            stdout="prefix/img1:tag1\nprefix/img2:tag2\n", returncode=0
        )
        imgs = docker_cleanup.get_images("prefix", 7)
        self.assertEqual(imgs, ["prefix/img1:tag1", "prefix/img2:tag2"])
        mock_run.assert_called_once_with(
            [
                "docker",
                "images",
                "--filter",
                "reference=prefix/*",
                "--filter",
                "until=168h",
                "--format",
                "{{.Repository}}:{{.Tag}}",
            ],
            capture_output=True,
            text=True,
            check=True,
        )

    @patch("scripts.docker_cleanup.subprocess.run")
    @patch("scripts.docker_cleanup.logging.warning")
    def test_get_images_exception(
        self, mock_warning: MagicMock, mock_run: MagicMock
    ) -> None:
        """Test get_images handles subprocess error."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "cmd")
        imgs = docker_cleanup.get_images("p", 7)
        self.assertEqual(imgs, [])
        mock_warning.assert_called_once()

    @patch("scripts.docker_cleanup.subprocess.Popen")
    @patch("scripts.docker_cleanup.logging.info")
    def test_cleanup_images_batch_logic(
        self, mock_logging_info: MagicMock, mock_popen: MagicMock
    ) -> None:
        """Test cleanup_images_batch successfully removes images."""
        mock_proc = MagicMock()
        mock_proc.poll.return_value = 0  # Process finished immediately
        mock_proc.returncode = 0
        mock_proc.communicate.return_value = ("stdout_msg\n", "stderr_msg\n")
        mock_proc.__enter__.return_value = mock_proc
        mock_popen.return_value = mock_proc

        cancel_event = Event()
        docker_cleanup.cleanup_images_batch(cancel_event, ["img1", "img2"])

        self.assertEqual(mock_popen.call_count, 2)
        mock_logging_info.assert_any_call("Removing image: %s", "img1")
        mock_logging_info.assert_any_call("Removing image: %s", "img2")
        mock_logging_info.assert_any_call("[docker rmi stdout]: %s", "stdout_msg")

    @patch("scripts.docker_cleanup.subprocess.Popen")
    @patch("scripts.docker_cleanup.logging.info")
    def test_cleanup_images_batch_cancel_before_start(
        self, mock_logging_info: MagicMock, mock_popen: MagicMock
    ) -> None:
        """Test cleanup_images_batch respects cancel_event before starting a process."""
        cancel_event = MagicMock(spec=Event)
        # cancel after first image log
        cancel_event.is_set.side_effect = [False, True]

        # Mock poll to return 0 immediately so it doesn't loop
        mock_proc = MagicMock()
        mock_proc.poll.return_value = 0
        mock_proc.returncode = 0
        mock_proc.__enter__.return_value = mock_proc
        mock_proc.communicate.return_value = ("", "")
        mock_popen.return_value = mock_proc

        docker_cleanup.cleanup_images_batch(cancel_event, ["img1", "img2"])

        mock_logging_info.assert_any_call("Removing image: %s", "img1")
        # Only one Popen call should happen
        self.assertEqual(mock_popen.call_count, 1)

    @patch("scripts.docker_cleanup.subprocess.Popen")
    @patch("scripts.docker_cleanup.logging.info")
    def test_cleanup_images_batch_cancel_during_poll(
        self, mock_logging_info: MagicMock, mock_popen: MagicMock
    ) -> None:
        """Test cleanup_images_batch exits during polling if cancel_event is set."""
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None  # Process is still running
        mock_proc.__enter__.return_value = mock_proc
        mock_popen.return_value = mock_proc

        cancel_event = MagicMock(spec=Event)
        # wait returns True, meaning event was set
        cancel_event.wait.return_value = True
        cancel_event.is_set.return_value = False

        docker_cleanup.cleanup_images_batch(cancel_event, ["img1"])

        mock_logging_info.assert_any_call(
            "Cleanup cancelled; exiting removal loop for %s", "img1"
        )
        # Process was started but we exited the loop
        self.assertEqual(mock_popen.call_count, 1)
        mock_proc.terminate.assert_called_once()

    @patch("scripts.docker_cleanup.subprocess.Popen")
    @patch("scripts.docker_cleanup.logging.warning")
    def test_cleanup_images_batch_failure(
        self, mock_logging_warning: MagicMock, mock_popen: MagicMock
    ) -> None:
        """Test cleanup_images_batch logs warning on process failure."""
        mock_proc = MagicMock()
        mock_proc.poll.return_value = 0
        mock_proc.returncode = 1
        mock_proc.__enter__.return_value = mock_proc
        mock_proc.communicate.return_value = ("", "error_msg\n")
        mock_popen.return_value = mock_proc

        cancel_event = Event()
        docker_cleanup.cleanup_images_batch(cancel_event, ["img1"])

        mock_logging_warning.assert_any_call("[docker rmi stderr]: %s", "error_msg")
        mock_logging_warning.assert_any_call(
            "Failed to remove image %s (exit code %d)", "img1", 1
        )

    @patch("scripts.docker_cleanup.subprocess.Popen")
    @patch("scripts.docker_cleanup.logging.warning")
    def test_cleanup_images_batch_exception(
        self, mock_logging_warning: MagicMock, mock_popen: MagicMock
    ) -> None:
        """Test cleanup_images_batch logs warning on exception."""
        mock_popen.side_effect = Exception("test error")

        cancel_event = Event()
        docker_cleanup.cleanup_images_batch(cancel_event, ["img1"])

        mock_logging_warning.assert_called_with(
            "Error during image removal of %s: %s", "img1", mock_popen.side_effect
        )

    def test_cleanup_images_batch_empty(self) -> None:
        """Test cleanup_images_batch with no images."""
        cancel_event = Event()
        with patch("scripts.docker_cleanup.logging.info") as mock_info:
            docker_cleanup.cleanup_images_batch(cancel_event, [])
            mock_info.assert_not_called()

    @patch(
        "sys.argv", ["docker_cleanup.py", "--config-path", "c", "--search-path", "s"]
    )
    @patch("scripts.docker_cleanup.cleanup_images")
    def test_main(self, mock_cleanup: MagicMock) -> None:
        """Test main manual entry point parsing."""
        docker_cleanup.main()
        mock_cleanup.assert_called_once()
        args, kwargs = mock_cleanup.call_args
        self.assertIsInstance(args[0], Event)
        self.assertEqual(args[1], Path("c"))
        self.assertEqual(args[2], [Path("s")])
        self.assertEqual(kwargs["initial_delay"], 0.0)
        self.assertEqual(kwargs["interval"], 0.0)
        self.assertEqual(kwargs["batch_size"], 10)
        self.assertEqual(
            kwargs["threshold_days"], docker_cleanup.CLEANUP_THRESHOLD_DAYS
        )

    @patch(
        "sys.argv", ["docker_cleanup.py", "--config-path", "c", "--search-path", "s"]
    )
    @patch("scripts.docker_cleanup.cleanup_images")
    @patch("scripts.docker_cleanup.logging.info")
    def test_main_keyboard_interrupt(
        self, mock_logging_info: MagicMock, mock_cleanup: MagicMock
    ) -> None:
        """Test main manual entry handles KeyboardInterrupt."""
        mock_cleanup.side_effect = KeyboardInterrupt()
        docker_cleanup.main()
        mock_logging_info.assert_any_call("Cleanup interrupted by user.")


class TestAllowlist(unittest.TestCase):
    """Tests for the image allowlist."""

    def test_all_dockerfiles_allowed(self) -> None:
        """Verify that all Dockerfiles in the images directory are allowed."""
        # Calculate images_dir relative to this test file.
        # This assumes the test file is in 'scripts/' and 'images/' is at the root.
        images_dir = Path(__file__).parent.parent / "images"
        dockerfiles = list(images_dir.glob("*.Dockerfile"))
        self.assertTrue(len(dockerfiles) > 0, f"No Dockerfiles found in {images_dir}")

        for df in dockerfiles:
            image_name = df.stem
            self.assertIn(
                image_name,
                docker_cleanup.ALLOWED_IMAGE_NAMES,
                f"Dockerfile '{df.name}' is not in ALLOWED_IMAGE_NAMES. "
                f"Please add '{image_name}' to the allowlist in "
                "scripts/docker_cleanup.py. "
                "DO NOT DELETE OLD ENTRIES from the allowlist.",
            )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
