"""Tests for sd_manager.py - SD card detection, mounting, formatting."""

import json
import os
from unittest.mock import patch, MagicMock

import pytest

from lib.sd_manager import (
    _ensure_block_device,
    _device_basename,
    _partition_device_for,
    _card_size_bytes,
    _validate_device,
    _validate_label,
    detect_sd_state,
    get_os_version,
    get_free_space,
    list_removable_drives,
    get_drive_partitions,
)
from lib.os_profiles import OS_PROFILES


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------

class TestEnsureBlockDevice:
    def test_adds_dev_prefix(self):
        assert _ensure_block_device("sda") == "/dev/sda"

    def test_keeps_existing_prefix(self):
        assert _ensure_block_device("/dev/sda") == "/dev/sda"

    def test_mmcblk_device(self):
        assert _ensure_block_device("mmcblk0") == "/dev/mmcblk0"


class TestDeviceBasename:
    def test_full_path(self):
        assert _device_basename("/dev/sda") == "sda"

    def test_bare_name(self):
        assert _device_basename("sda") == "sda"


class TestPartitionDeviceFor:
    def test_sd_device(self):
        assert _partition_device_for("/dev/sda") == "/dev/sda1"

    def test_nvme_style_device(self):
        assert _partition_device_for("/dev/mmcblk0") == "/dev/mmcblk0p1"

    def test_nvme_device(self):
        assert _partition_device_for("/dev/nvme0n1") == "/dev/nvme0n1p1"


class TestValidateDevice:
    def test_valid_sd_device(self):
        _validate_device("/dev/sda")

    def test_valid_mmcblk(self):
        _validate_device("/dev/mmcblk0")

    def test_rejects_path_traversal(self):
        with pytest.raises(ValueError):
            _validate_device("/dev/../etc/passwd")

    def test_rejects_shell_injection(self):
        with pytest.raises(ValueError):
            _validate_device("/dev/sda; rm -rf /")

    def test_rejects_spaces(self):
        with pytest.raises(ValueError):
            _validate_device("/dev/my device")

    def test_rejects_no_dev_prefix(self):
        with pytest.raises(ValueError):
            _validate_device("sda")


class TestValidateLabel:
    def test_valid_label(self):
        _validate_label("CROSSMIX")

    def test_valid_with_numbers(self):
        _validate_label("SD32GB")

    def test_rejects_special_chars(self):
        with pytest.raises(ValueError):
            _validate_label("LABEL;rm")

    def test_rejects_too_long(self):
        with pytest.raises(ValueError):
            _validate_label("A" * 12)

    def test_empty_is_valid(self):
        _validate_label("")

    def test_sdcard_is_valid(self):
        _validate_label("SDCARD")


class TestCardSizeBytes:
    @patch("builtins.open", create=True)
    def test_reads_sysfs(self, mock_open):
        mock_open.return_value.__enter__ = MagicMock(
            return_value=MagicMock(read=MagicMock(return_value="125042688\n"), strip=None)
        )
        mock_open.return_value.__exit__ = MagicMock(return_value=False)

    def test_missing_sysfs_returns_zero(self):
        result = _card_size_bytes("/dev/nonexistent_fake_device_xyz")
        assert result == 0


# ---------------------------------------------------------------------------
# detect_sd_state
# ---------------------------------------------------------------------------

class TestDetectSdState:
    def test_nonexistent_dir(self, tmp_path):
        result = detect_sd_state(str(tmp_path / "nonexistent"))
        assert result == "unknown"

    def test_empty_sd(self, tmp_path):
        result = detect_sd_state(str(tmp_path))
        assert result == "empty"

    def test_empty_with_system_dirs_only(self, tmp_path):
        (tmp_path / "System Volume Information").mkdir()
        result = detect_sd_state(str(tmp_path))
        assert result == "empty"

    def test_detect_onion(self, tmp_path):
        (tmp_path / ".tmp_update").mkdir()
        result = detect_sd_state(str(tmp_path))
        assert result == "onion"

    def test_detect_crossmix(self, tmp_path):
        (tmp_path / "System").mkdir()
        (tmp_path / "Emus").mkdir()
        result = detect_sd_state(str(tmp_path))
        assert result == "crossmix"

    def test_detect_stock_miyoo(self, tmp_path):
        (tmp_path / "miyoo").mkdir()
        result = detect_sd_state(str(tmp_path))
        assert result == "stock"

    def test_unknown_content(self, tmp_path):
        (tmp_path / "random_stuff").mkdir()
        result = detect_sd_state(str(tmp_path))
        assert result == "unknown"

    def test_onion_takes_priority_over_stock(self, tmp_path):
        """If both .tmp_update and miyoo exist, it should detect as onion."""
        (tmp_path / ".tmp_update").mkdir()
        (tmp_path / "miyoo").mkdir()
        result = detect_sd_state(str(tmp_path))
        assert result == "onion"

    def test_crossmix_needs_both_markers(self, tmp_path):
        """System alone without Emus should not detect as crossmix."""
        (tmp_path / "System").mkdir()
        (tmp_path / "something_else").mkdir()
        result = detect_sd_state(str(tmp_path))
        assert result == "unknown"

    def test_detect_minui(self, tmp_path):
        (tmp_path / "MinUI.zip").write_bytes(b"")
        (tmp_path / "trimui").mkdir()
        result = detect_sd_state(str(tmp_path))
        assert result == "minui"

    def test_detect_koriki(self, tmp_path):
        (tmp_path / "Koriki").mkdir()
        (tmp_path / ".simplemenu").mkdir()
        result = detect_sd_state(str(tmp_path))
        assert result == "koriki"

    def test_detect_myminui(self, tmp_path):
        (tmp_path / "MinUI.zip").write_bytes(b"")
        result = detect_sd_state(str(tmp_path))
        assert result == "myminui"


# ---------------------------------------------------------------------------
# get_os_version
# ---------------------------------------------------------------------------

class TestGetOsVersion:
    def test_reads_version_file(self, tmp_path):
        version_dir = tmp_path / ".tmp_update" / "onionVersion"
        version_dir.mkdir(parents=True)
        (version_dir / "version.txt").write_text("4.3.1\n")

        profile = {"version_paths": [".tmp_update/onionVersion/version.txt"]}
        result = get_os_version(str(tmp_path), profile)
        assert result == "4.3.1"

    def test_tries_multiple_paths(self, tmp_path):
        # First path doesn't exist, second does
        (tmp_path / "System").mkdir()
        (tmp_path / "System" / "crossmix_version.txt").write_text("1.3.0")

        profile = {
            "version_paths": [
                "System/usr/trimui/crossmix_version.txt",
                "System/crossmix_version.txt",
            ]
        }
        result = get_os_version(str(tmp_path), profile)
        assert result == "1.3.0"

    def test_no_version_file(self, tmp_path):
        profile = {"version_paths": ["nonexistent/version.txt"]}
        result = get_os_version(str(tmp_path), profile)
        assert result is None

    def test_empty_version_paths(self, tmp_path):
        profile = {"version_paths": []}
        result = get_os_version(str(tmp_path), profile)
        assert result is None

    @pytest.mark.parametrize("profile_key", list(OS_PROFILES.keys()))
    def test_get_version_doesnt_crash_on_any_profile(self, tmp_path, profile_key):
        result = get_os_version(str(tmp_path), OS_PROFILES[profile_key])
        assert result is None  # no version files exist in tmp_path


# ---------------------------------------------------------------------------
# list_removable_drives (mocked)
# ---------------------------------------------------------------------------

class TestListRemovableDrives:
    @patch("lib.sd_manager._run")
    def test_finds_removable_disk(self, mock_run):
        lsblk_output = {
            "blockdevices": [
                {
                    "name": "sda",
                    "size": "32G",
                    "type": "disk",
                    "mountpoint": None,
                    "fstype": None,
                    "rm": True,
                    "model": "SD Card Reader",
                    "tran": "usb",
                    "label": None,
                    "children": [],
                }
            ]
        }
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps(lsblk_output),
        )
        drives = list_removable_drives()
        assert len(drives) == 1
        assert drives[0]["name"] == "sda"
        assert drives[0]["device"] == "/dev/sda"

    @patch("lib.sd_manager._run")
    def test_filters_non_removable(self, mock_run):
        lsblk_output = {
            "blockdevices": [
                {
                    "name": "sda",
                    "size": "500G",
                    "type": "disk",
                    "mountpoint": None,
                    "fstype": None,
                    "rm": False,
                    "model": "Internal SSD",
                    "tran": "sata",
                    "label": None,
                    "children": [],
                }
            ]
        }
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps(lsblk_output),
        )
        drives = list_removable_drives()
        assert len(drives) == 0

    @patch("lib.sd_manager._run")
    def test_filters_non_disk_types(self, mock_run):
        lsblk_output = {
            "blockdevices": [
                {
                    "name": "sda1",
                    "size": "32G",
                    "type": "part",
                    "mountpoint": "/media/sd",
                    "fstype": "vfat",
                    "rm": True,
                    "model": "",
                    "tran": None,
                    "label": "SDCARD",
                    "children": [],
                }
            ]
        }
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps(lsblk_output),
        )
        drives = list_removable_drives()
        assert len(drives) == 0

    @patch("lib.sd_manager._run")
    def test_handles_string_rm_field(self, mock_run):
        """Some lsblk versions return rm as "1" string instead of bool."""
        lsblk_output = {
            "blockdevices": [
                {
                    "name": "sda",
                    "size": "32G",
                    "type": "disk",
                    "mountpoint": None,
                    "fstype": None,
                    "rm": "1",
                    "model": "SD Reader",
                    "tran": "usb",
                    "label": None,
                    "children": [],
                }
            ]
        }
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps(lsblk_output),
        )
        drives = list_removable_drives()
        assert len(drives) == 1

    @patch("lib.sd_manager._run")
    def test_lsblk_failure(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stderr="error", stdout="")
        drives = list_removable_drives()
        assert drives == []

    @patch("lib.sd_manager._run")
    def test_invalid_json(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="not json")
        drives = list_removable_drives()
        assert drives == []


# ---------------------------------------------------------------------------
# get_drive_partitions (mocked)
# ---------------------------------------------------------------------------

class TestGetDrivePartitions:
    @patch("lib.sd_manager._run")
    def test_returns_partitions(self, mock_run):
        lsblk_output = {
            "blockdevices": [
                {
                    "name": "sda",
                    "children": [
                        {
                            "name": "sda1",
                            "size": "32G",
                            "type": "part",
                            "mountpoint": "/media/sd",
                            "fstype": "vfat",
                            "label": "CROSSMIX",
                        }
                    ],
                }
            ]
        }
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps(lsblk_output),
        )
        parts = get_drive_partitions("/dev/sda")
        assert len(parts) == 1
        assert parts[0]["label"] == "CROSSMIX"
        assert parts[0]["device"] == "/dev/sda1"


# ---------------------------------------------------------------------------
# get_free_space
# ---------------------------------------------------------------------------

class TestGetFreeSpace:
    def test_returns_positive_for_existing_path(self, tmp_path):
        space = get_free_space(str(tmp_path))
        assert space > 0

    def test_returns_zero_for_nonexistent(self):
        space = get_free_space("/nonexistent/path/xyz")
        assert space == 0
