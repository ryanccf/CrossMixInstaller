"""Tests for sd_manager_win.py - Windows SD card operations.

All PowerShell/subprocess calls are mocked so tests run on any platform.
"""

import json
import os
import subprocess
from unittest.mock import patch, MagicMock, mock_open, call

import pytest

from lib.sd_manager_win import (
    _ps,
    _ps_json,
    _is_admin,
    _elevate_and_run,
    _disk_number_from_device,
    list_removable_drives,
    get_drive_partitions,
    format_sd_card,
    check_disk,
    eject_drive,
    mount_partition,
    unmount_partition,
    unmount_all_partitions,
    write_image_to_device,
)


# ---------------------------------------------------------------------------
# _ps helper
# ---------------------------------------------------------------------------

class TestPs:
    @patch("lib.sd_manager_win.subprocess.run")
    def test_runs_powershell_command(self, mock_run):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="output", stderr="",
        )
        result = _ps("Get-Disk")
        mock_run.assert_called_once_with(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", "Get-Disk"],
            capture_output=True, text=True, timeout=120,
        )
        assert result.returncode == 0
        assert result.stdout == "output"

    @patch("lib.sd_manager_win.subprocess.run")
    def test_custom_timeout(self, mock_run):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr="",
        )
        _ps("Get-Disk", timeout=30)
        mock_run.assert_called_once()
        assert mock_run.call_args.kwargs["timeout"] == 30


# ---------------------------------------------------------------------------
# _ps_json helper
# ---------------------------------------------------------------------------

class TestPsJson:
    @patch("lib.sd_manager_win._ps")
    def test_parses_json_output(self, mock_ps):
        data = {"Number": 2, "Size": 32000000000}
        mock_ps.return_value = subprocess.CompletedProcess(
            args=[], returncode=0,
            stdout=json.dumps(data), stderr="",
        )
        result = _ps_json("Get-Disk")
        assert result == data
        # Verifies ConvertTo-Json is appended
        assert "ConvertTo-Json" in mock_ps.call_args[0][0]

    @patch("lib.sd_manager_win._ps")
    def test_returns_none_on_failure(self, mock_ps):
        mock_ps.return_value = subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr="error msg",
        )
        assert _ps_json("bad-cmd") is None

    @patch("lib.sd_manager_win._ps")
    def test_returns_none_on_empty_output(self, mock_ps):
        mock_ps.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr="",
        )
        assert _ps_json("Get-Disk") is None

    @patch("lib.sd_manager_win._ps")
    def test_returns_none_on_invalid_json(self, mock_ps):
        mock_ps.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="not json {{{", stderr="",
        )
        assert _ps_json("Get-Disk") is None


# ---------------------------------------------------------------------------
# _disk_number_from_device
# ---------------------------------------------------------------------------

class TestDiskNumberFromDevice:
    def test_bare_number(self):
        assert _disk_number_from_device("2") == 2

    def test_physical_drive_path(self):
        assert _disk_number_from_device("\\\\.\\PhysicalDrive3") == 3

    def test_physical_drive_name(self):
        assert _disk_number_from_device("PhysicalDrive0") == 0

    def test_disk_name(self):
        assert _disk_number_from_device("Disk1") == 1

    def test_no_number(self):
        assert _disk_number_from_device("abc") is None

    def test_empty_string(self):
        assert _disk_number_from_device("") is None

    def test_multi_digit(self):
        assert _disk_number_from_device("PhysicalDrive12") == 12


# ---------------------------------------------------------------------------
# _is_admin
# ---------------------------------------------------------------------------

class TestIsAdmin:
    @patch("lib.sd_manager_win.ctypes")
    def test_returns_true_when_admin(self, mock_ctypes):
        mock_ctypes.windll.shell32.IsUserAnAdmin.return_value = 1
        assert _is_admin() is True

    @patch("lib.sd_manager_win.ctypes")
    def test_returns_false_when_not_admin(self, mock_ctypes):
        mock_ctypes.windll.shell32.IsUserAnAdmin.return_value = 0
        assert _is_admin() is False

    @patch("lib.sd_manager_win.ctypes")
    def test_returns_false_on_exception(self, mock_ctypes):
        mock_ctypes.windll.shell32.IsUserAnAdmin.side_effect = AttributeError
        assert _is_admin() is False


# ---------------------------------------------------------------------------
# _elevate_and_run
# ---------------------------------------------------------------------------

class TestElevateAndRun:
    @patch("lib.sd_manager_win._is_admin", return_value=True)
    @patch("lib.sd_manager_win._ps")
    def test_runs_directly_when_admin(self, mock_ps, mock_admin):
        mock_ps.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="ok", stderr="",
        )
        result = _elevate_and_run("some-script")
        mock_ps.assert_called_once_with("some-script", timeout=300)
        assert result.stdout == "ok"

    @patch("lib.sd_manager_win._is_admin", return_value=False)
    @patch("lib.sd_manager_win.ctypes")
    @patch("lib.sd_manager_win.os.path.exists")
    @patch("lib.sd_manager_win.os.unlink")
    @patch("builtins.open", new_callable=mock_open, read_data="elevated output")
    @patch("lib.sd_manager_win.tempfile.NamedTemporaryFile")
    def test_elevates_via_uac_when_not_admin(
        self, mock_tmp, mock_file_open, mock_unlink, mock_exists,
        mock_ctypes, mock_admin,
    ):
        # Setup temp file
        mock_f = MagicMock()
        mock_f.name = "C:\\tmp\\script.ps1"
        mock_f.__enter__ = MagicMock(return_value=mock_f)
        mock_f.__exit__ = MagicMock(return_value=False)
        mock_tmp.return_value = mock_f

        mock_ctypes.windll.shell32.ShellExecuteW.return_value = 42  # > 32 = success
        mock_exists.return_value = True  # output file exists

        result = _elevate_and_run("test-script", timeout=5)
        assert result.returncode == 0
        mock_ctypes.windll.shell32.ShellExecuteW.assert_called_once()

    @patch("lib.sd_manager_win._is_admin", return_value=False)
    @patch("lib.sd_manager_win.ctypes")
    @patch("lib.sd_manager_win.os.unlink")
    @patch("lib.sd_manager_win.tempfile.NamedTemporaryFile")
    def test_uac_denied(self, mock_tmp, mock_unlink, mock_ctypes, mock_admin):
        mock_f = MagicMock()
        mock_f.name = "C:\\tmp\\script.ps1"
        mock_f.__enter__ = MagicMock(return_value=mock_f)
        mock_f.__exit__ = MagicMock(return_value=False)
        mock_tmp.return_value = mock_f

        mock_ctypes.windll.shell32.ShellExecuteW.return_value = 5  # <= 32 = failure
        result = _elevate_and_run("test-script")
        assert result.returncode == 1
        assert "denied" in result.stderr.lower() or "failed" in result.stderr.lower()


# ---------------------------------------------------------------------------
# list_removable_drives
# ---------------------------------------------------------------------------

class TestListRemovableDrives:
    @patch("lib.sd_manager_win._ps_json")
    def test_returns_empty_when_no_disks(self, mock_ps_json):
        mock_ps_json.return_value = None
        assert list_removable_drives() == []

    @patch("lib.sd_manager_win._ps_json")
    def test_single_disk_returned_as_dict(self, mock_ps_json):
        """PowerShell returns a single object (not array) for one result."""
        disk = {
            "Number": 2,
            "FriendlyName": "Generic SD Reader",
            "Size": 32000000000,
            "BusType": "USB",
            "PartitionStyle": "MBR",
        }
        partition = {
            "PartitionNumber": 1,
            "DriveLetter": "E",
            "Size": 31900000000,
            "Type": "Basic",
        }
        volume = {
            "FileSystemLabel": "CROSSMIX",
            "FileSystem": "FAT32",
            "SizeRemaining": 15000000000,
        }

        def side_effect(script, **kwargs):
            if "Get-Disk" in script:
                return disk
            if "Get-Partition" in script:
                return partition
            if "Get-Volume" in script:
                return volume
            return None

        mock_ps_json.side_effect = side_effect

        drives = list_removable_drives()
        assert len(drives) == 1
        d = drives[0]
        assert d["name"] == "Disk2"
        assert d["device"] == "\\\\.\\PhysicalDrive2"
        assert d["rm"] is True
        assert d["model"] == "Generic SD Reader"
        assert d["tran"] == "USB"
        assert d["label"] == "CROSSMIX"
        assert d["size"] == "29.8G"
        assert d["type"] == "disk"
        assert len(d["children"]) == 1
        assert d["children"][0]["name"] == "E:"
        assert d["children"][0]["mountpoint"] == "E:\\"
        assert d["children"][0]["fstype"] == "FAT32"
        assert d["children"][0]["label"] == "CROSSMIX"

    @patch("lib.sd_manager_win._ps_json")
    def test_multiple_disks(self, mock_ps_json):
        disks = [
            {"Number": 1, "FriendlyName": "Reader A", "Size": 16000000000, "BusType": "USB"},
            {"Number": 2, "FriendlyName": "Reader B", "Size": 64000000000, "BusType": "SD"},
        ]

        def side_effect(script, **kwargs):
            if "Get-Disk" in script:
                return disks
            if "Get-Partition" in script:
                return None
            return None

        mock_ps_json.side_effect = side_effect

        drives = list_removable_drives()
        assert len(drives) == 2
        assert drives[0]["name"] == "Disk1"
        assert drives[1]["name"] == "Disk2"

    @patch("lib.sd_manager_win._ps_json")
    def test_disk_without_drive_letter(self, mock_ps_json):
        disk = {"Number": 3, "FriendlyName": "Card", "Size": 8000000000, "BusType": "USB"}
        partition = {"PartitionNumber": 1, "DriveLetter": None, "Size": 8000000000, "Type": "Basic"}

        def side_effect(script, **kwargs):
            if "Get-Disk" in script:
                return disk
            if "Get-Partition" in script:
                return partition
            return None

        mock_ps_json.side_effect = side_effect

        drives = list_removable_drives()
        assert len(drives) == 1
        assert drives[0]["mountpoint"] is None
        assert drives[0]["children"] == []

    @patch("lib.sd_manager_win._ps_json")
    def test_size_formatting_megabytes(self, mock_ps_json):
        disk = {"Number": 1, "FriendlyName": "Small", "Size": 512 * 1024 * 1024, "BusType": "USB"}

        def side_effect(script, **kwargs):
            if "Get-Disk" in script:
                return disk
            return None

        mock_ps_json.side_effect = side_effect

        drives = list_removable_drives()
        assert drives[0]["size"] == "512M"

    @patch("lib.sd_manager_win._ps_json")
    def test_size_formatting_bytes(self, mock_ps_json):
        disk = {"Number": 1, "FriendlyName": "Tiny", "Size": 1000, "BusType": "USB"}

        def side_effect(script, **kwargs):
            if "Get-Disk" in script:
                return disk
            return None

        mock_ps_json.side_effect = side_effect

        drives = list_removable_drives()
        assert drives[0]["size"] == "1000"


# ---------------------------------------------------------------------------
# get_drive_partitions
# ---------------------------------------------------------------------------

class TestGetDrivePartitions:
    @patch("lib.sd_manager_win._ps_json")
    def test_returns_partitions_with_drive_letter(self, mock_ps_json):
        partition = {
            "PartitionNumber": 1,
            "DriveLetter": "E",
            "Size": 32000000000,
            "Type": "Basic",
        }
        volume = {"FileSystemLabel": "SDCARD", "FileSystem": "FAT32"}

        def side_effect(script, **kwargs):
            if "Get-Partition" in script:
                return partition
            if "Get-Volume" in script:
                return volume
            return None

        mock_ps_json.side_effect = side_effect

        parts = get_drive_partitions("\\\\.\\PhysicalDrive2")
        assert len(parts) == 1
        assert parts[0]["name"] == "E:"
        assert parts[0]["device"] == "E:"
        assert parts[0]["mountpoint"] == "E:\\"
        assert parts[0]["fstype"] == "FAT32"
        assert parts[0]["label"] == "SDCARD"

    @patch("lib.sd_manager_win._ps_json")
    def test_partition_without_drive_letter(self, mock_ps_json):
        partition = {"PartitionNumber": 1, "DriveLetter": None, "Size": 16000000000, "Type": "Basic"}

        def side_effect(script, **kwargs):
            if "Get-Partition" in script:
                return partition
            return None

        mock_ps_json.side_effect = side_effect

        parts = get_drive_partitions("2")
        assert len(parts) == 1
        assert parts[0]["name"] == "Part1"
        assert parts[0]["device"] == "Disk2p1"
        assert parts[0]["mountpoint"] is None

    @patch("lib.sd_manager_win._ps_json")
    def test_returns_empty_for_invalid_device(self, mock_ps_json):
        parts = get_drive_partitions("abc")
        assert parts == []
        mock_ps_json.assert_not_called()

    @patch("lib.sd_manager_win._ps_json")
    def test_returns_empty_when_ps_fails(self, mock_ps_json):
        mock_ps_json.return_value = None
        parts = get_drive_partitions("2")
        assert parts == []

    @patch("lib.sd_manager_win._ps_json")
    def test_multiple_partitions(self, mock_ps_json):
        partitions = [
            {"PartitionNumber": 1, "DriveLetter": "E", "Size": 16000000000, "Type": "Basic"},
            {"PartitionNumber": 2, "DriveLetter": "F", "Size": 16000000000, "Type": "Basic"},
        ]
        vol_e = {"FileSystemLabel": "BOOT", "FileSystem": "FAT32"}
        vol_f = {"FileSystemLabel": "DATA", "FileSystem": "NTFS"}

        call_count = {"partition": 0, "volume": 0}

        def side_effect(script, **kwargs):
            if "Get-Partition" in script:
                return partitions
            if "Get-Volume" in script:
                if "'E'" in script:
                    return vol_e
                if "'F'" in script:
                    return vol_f
            return None

        mock_ps_json.side_effect = side_effect

        parts = get_drive_partitions("1")
        assert len(parts) == 2
        assert parts[0]["label"] == "BOOT"
        assert parts[1]["label"] == "DATA"

    @patch("lib.sd_manager_win._ps_json")
    def test_empty_drive_letter_string(self, mock_ps_json):
        """DriveLetter that is an empty/whitespace string should be treated as None."""
        partition = {"PartitionNumber": 1, "DriveLetter": "  ", "Size": 8000000000, "Type": "Basic"}

        def side_effect(script, **kwargs):
            if "Get-Partition" in script:
                return partition
            return None

        mock_ps_json.side_effect = side_effect

        parts = get_drive_partitions("1")
        assert len(parts) == 1
        assert parts[0]["name"] == "Part1"
        assert parts[0]["mountpoint"] is None


# ---------------------------------------------------------------------------
# format_sd_card
# ---------------------------------------------------------------------------

class TestFormatSdCard:
    @patch("lib.sd_manager_win._elevate_and_run")
    @patch("lib.sd_manager_win.os.unlink")
    def test_successful_format(self, mock_unlink, mock_elevate):
        mock_elevate.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="DiskPart succeeded", stderr="",
        )
        ok, msg = format_sd_card("\\\\.\\PhysicalDrive2", "CROSSMIX")
        assert ok is True
        assert "FAT32" in msg
        assert "Disk 2" in msg

    @patch("lib.sd_manager_win._elevate_and_run")
    @patch("lib.sd_manager_win.os.unlink")
    def test_format_with_cluster_sectors_fn(self, mock_unlink, mock_elevate):
        mock_elevate.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="ok", stderr="",
        )
        with patch("lib.sd_manager_win._ps_json", return_value=64000000000):
            ok, msg = format_sd_card("2", cluster_sectors_fn=lambda sz: "128")
        assert ok is True

    def test_invalid_device_returns_error(self):
        ok, msg = format_sd_card("abc")
        assert ok is False
        assert "Cannot determine disk number" in msg

    @patch("lib.sd_manager_win._elevate_and_run")
    @patch("lib.sd_manager_win.os.unlink")
    def test_invalid_label_returns_error(self, mock_unlink, mock_elevate):
        ok, msg = format_sd_card("2", label="BAD;LABEL!")
        assert ok is False
        assert "Invalid volume label" in msg

    @patch("lib.sd_manager_win._elevate_and_run")
    @patch("lib.sd_manager_win.os.unlink")
    def test_format_failure(self, mock_unlink, mock_elevate):
        mock_elevate.return_value = subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr="Access denied error",
        )
        ok, msg = format_sd_card("2")
        assert ok is False
        assert "Format failed" in msg

    @patch("lib.sd_manager_win._elevate_and_run")
    @patch("lib.sd_manager_win.os.unlink")
    def test_format_error_in_stderr(self, mock_unlink, mock_elevate):
        mock_elevate.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr="diskpart error occurred",
        )
        ok, msg = format_sd_card("2")
        assert ok is False

    @patch("lib.sd_manager_win._elevate_and_run")
    @patch("lib.sd_manager_win.os.unlink")
    def test_default_label(self, mock_unlink, mock_elevate):
        mock_elevate.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="ok", stderr="",
        )
        ok, msg = format_sd_card("2")
        assert ok is True
        assert "SDCARD" in msg

    @patch("lib.sd_manager_win._elevate_and_run")
    @patch("lib.sd_manager_win.os.unlink")
    def test_label_truncated_to_11_chars(self, mock_unlink, mock_elevate):
        mock_elevate.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="ok", stderr="",
        )
        ok, msg = format_sd_card("2", label="TOOLONGNAME1")
        assert ok is True
        assert "TOOLONGNAME" in msg  # 11 chars

    @patch("lib.sd_manager_win._elevate_and_run")
    @patch("lib.sd_manager_win.os.unlink")
    def test_none_label_defaults(self, mock_unlink, mock_elevate):
        mock_elevate.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="ok", stderr="",
        )
        ok, msg = format_sd_card("2", label=None)
        assert ok is True
        assert "SDCARD" in msg


# ---------------------------------------------------------------------------
# check_disk
# ---------------------------------------------------------------------------

class TestCheckDisk:
    @patch("lib.sd_manager_win._elevate_and_run")
    def test_valid_drive_letter(self, mock_elevate):
        mock_elevate.return_value = subprocess.CompletedProcess(
            args=[], returncode=0,
            stdout="Windows has scanned the file system and found no problems.",
            stderr="",
        )
        result = check_disk("E:")
        assert "no problems" in result
        mock_elevate.assert_called_once()
        assert "chkdsk E:" in mock_elevate.call_args[0][0]

    @patch("lib.sd_manager_win._elevate_and_run")
    def test_drive_letter_without_colon(self, mock_elevate):
        mock_elevate.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="OK", stderr="",
        )
        result = check_disk("E")
        assert "chkdsk E:" in mock_elevate.call_args[0][0]

    @patch("lib.sd_manager_win._elevate_and_run")
    def test_drive_letter_with_backslash(self, mock_elevate):
        mock_elevate.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="OK", stderr="",
        )
        result = check_disk("E:\\")
        assert "chkdsk E:" in mock_elevate.call_args[0][0]

    def test_invalid_partition_name(self):
        result = check_disk("InvalidPath")
        assert "Invalid partition" in result

    @patch("lib.sd_manager_win._elevate_and_run")
    def test_combines_stdout_and_stderr(self, mock_elevate):
        mock_elevate.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="out", stderr="err",
        )
        result = check_disk("E:")
        assert "out" in result
        assert "err" in result


# ---------------------------------------------------------------------------
# eject_drive
# ---------------------------------------------------------------------------

class TestEjectDrive:
    @patch("lib.sd_manager_win._ps")
    @patch("lib.sd_manager_win.get_drive_partitions")
    def test_successful_eject(self, mock_parts, mock_ps):
        mock_parts.return_value = [
            {"name": "E:", "device": "E:", "mountpoint": "E:\\"},
        ]
        mock_ps.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr="",
        )
        ok, msg = eject_drive("\\\\.\\PhysicalDrive2")
        assert ok is True
        assert "safely ejected" in msg

    @patch("lib.sd_manager_win._ps")
    @patch("lib.sd_manager_win.get_drive_partitions")
    def test_eject_with_set_offline_failure_still_succeeds(self, mock_parts, mock_ps):
        """Even if Set-Disk offline fails, we return True with dismount message."""
        mock_parts.return_value = []

        mock_ps.return_value = subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr="error",
        )
        ok, msg = eject_drive("2")
        assert ok is True
        assert "dismounted" in msg or "safely ejected" in msg

    def test_invalid_device(self):
        ok, msg = eject_drive("abc")
        assert ok is False
        assert "Cannot determine disk number" in msg

    @patch("lib.sd_manager_win._ps")
    @patch("lib.sd_manager_win.get_drive_partitions")
    def test_dismounts_multiple_partitions(self, mock_parts, mock_ps):
        mock_parts.return_value = [
            {"name": "E:", "device": "E:", "mountpoint": "E:\\"},
            {"name": "F:", "device": "F:", "mountpoint": "F:\\"},
        ]
        mock_ps.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr="",
        )
        ok, msg = eject_drive("2")
        assert ok is True
        # Should have called _ps for dismount E, dismount F, and Set-Disk offline
        assert mock_ps.call_count == 3


# ---------------------------------------------------------------------------
# mount_partition
# ---------------------------------------------------------------------------

class TestMountPartition:
    def test_drive_letter_path_exists(self, tmp_path):
        # Use an existing directory as a "drive letter" (works cross-platform in test)
        with patch("lib.sd_manager_win.re.match") as mock_match, \
             patch("lib.sd_manager_win.os.path.isdir", return_value=True):
            mock_match.return_value = True
            result = mount_partition("E:")
            assert result == "E:\\"

    def test_drive_letter_path_not_exists(self):
        with patch("lib.sd_manager_win.os.path.isdir", return_value=False):
            result = mount_partition("Z:")
            assert result is None

    @patch("lib.sd_manager_win.get_drive_partitions")
    def test_disk_number_with_existing_mountpoint(self, mock_parts):
        mock_parts.return_value = [
            {"name": "E:", "device": "E:", "mountpoint": "E:\\", "fstype": "FAT32"},
        ]
        result = mount_partition("2")
        assert result == "E:\\"

    @patch("lib.sd_manager_win._ps")
    @patch("lib.sd_manager_win.get_drive_partitions")
    def test_disk_number_assigns_drive_letter(self, mock_parts, mock_ps):
        # First call: no mountpoint. Second call (after assignment): has mountpoint.
        mock_parts.side_effect = [
            [{"name": "Part1", "device": "Disk2p1", "mountpoint": None}],
            [{"name": "F:", "device": "F:", "mountpoint": "F:\\"}],
        ]
        mock_ps.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr="",
        )
        result = mount_partition("2")
        assert result == "F:\\"

    @patch("lib.sd_manager_win.get_drive_partitions")
    def test_returns_none_when_no_mountpoint(self, mock_parts):
        mock_parts.return_value = [
            {"name": "Part1", "device": "Disk5p1", "mountpoint": None},
        ]
        with patch("lib.sd_manager_win._ps") as mock_ps:
            mock_ps.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="", stderr="",
            )
            # After assign attempt, still no mountpoint
            mock_parts.side_effect = [
                [{"name": "Part1", "device": "Disk5p1", "mountpoint": None}],
                [{"name": "Part1", "device": "Disk5p1", "mountpoint": None}],
            ]
            result = mount_partition("5")
            assert result is None

    def test_returns_none_for_invalid_input(self):
        result = mount_partition("not-a-device")
        assert result is None


# ---------------------------------------------------------------------------
# unmount_partition
# ---------------------------------------------------------------------------

class TestUnmountPartition:
    @patch("lib.sd_manager_win._ps")
    def test_successful_unmount(self, mock_ps):
        mock_ps.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr="",
        )
        ok, msg = unmount_partition("E:")
        assert ok is True
        assert "Unmounted" in msg

    @patch("lib.sd_manager_win._ps")
    def test_unmount_without_colon(self, mock_ps):
        mock_ps.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr="",
        )
        ok, msg = unmount_partition("E")
        assert ok is True

    @patch("lib.sd_manager_win._ps")
    def test_unmount_with_backslash(self, mock_ps):
        mock_ps.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr="",
        )
        ok, msg = unmount_partition("E:\\")
        assert ok is True

    @patch("lib.sd_manager_win._ps")
    def test_unmount_failure(self, mock_ps):
        mock_ps.return_value = subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr="Access denied",
        )
        ok, msg = unmount_partition("E:")
        assert ok is False
        assert "Failed to unmount" in msg

    def test_invalid_partition(self):
        ok, msg = unmount_partition("InvalidPath")
        assert ok is False
        assert "Invalid partition" in msg


# ---------------------------------------------------------------------------
# unmount_all_partitions
# ---------------------------------------------------------------------------

class TestUnmountAllPartitions:
    @patch("lib.sd_manager_win.unmount_partition")
    @patch("lib.sd_manager_win.get_drive_partitions")
    def test_unmounts_all_mounted(self, mock_parts, mock_unmount):
        mock_parts.return_value = [
            {"name": "E:", "device": "E:", "mountpoint": "E:\\"},
            {"name": "F:", "device": "F:", "mountpoint": "F:\\"},
        ]
        mock_unmount.return_value = (True, "OK")

        ok, msg = unmount_all_partitions("2")
        assert ok is True
        assert mock_unmount.call_count == 2

    @patch("lib.sd_manager_win.unmount_partition")
    @patch("lib.sd_manager_win.get_drive_partitions")
    def test_skips_unmounted_partitions(self, mock_parts, mock_unmount):
        mock_parts.return_value = [
            {"name": "E:", "device": "E:", "mountpoint": "E:\\"},
            {"name": "Part2", "device": "Disk2p2", "mountpoint": None},
        ]
        mock_unmount.return_value = (True, "OK")

        ok, msg = unmount_all_partitions("2")
        assert ok is True
        assert mock_unmount.call_count == 1

    @patch("lib.sd_manager_win.unmount_partition")
    @patch("lib.sd_manager_win.get_drive_partitions")
    def test_reports_failures(self, mock_parts, mock_unmount):
        mock_parts.return_value = [
            {"name": "E:", "device": "E:", "mountpoint": "E:\\"},
        ]
        mock_unmount.return_value = (False, "Error")

        ok, msg = unmount_all_partitions("2")
        assert ok is False
        assert "Failed to unmount" in msg
        assert "E:" in msg

    @patch("lib.sd_manager_win.get_drive_partitions")
    def test_no_partitions(self, mock_parts):
        mock_parts.return_value = []
        ok, msg = unmount_all_partitions("2")
        assert ok is True


# ---------------------------------------------------------------------------
# write_image_to_device
# ---------------------------------------------------------------------------

class TestWriteImageToDevice:
    @patch("lib.sd_manager_win._elevate_and_run")
    @patch("lib.sd_manager_win.unmount_all_partitions")
    @patch("lib.sd_manager_win.os.path.getsize", return_value=1024 * 1024)
    @patch("lib.sd_manager_win.os.path.isfile", return_value=True)
    def test_successful_write(self, mock_isfile, mock_size, mock_unmount, mock_elevate):
        mock_unmount.return_value = (True, "OK")
        mock_elevate.return_value = subprocess.CompletedProcess(
            args=[], returncode=0,
            stdout="Successfully wrote 1048576 bytes",
            stderr="",
        )
        ok, msg = write_image_to_device("/tmp/test.img", "\\\\.\\PhysicalDrive2")
        assert ok is True
        assert "PhysicalDrive2" in msg
        mock_unmount.assert_called_once()

    def test_invalid_device(self):
        ok, msg = write_image_to_device("/tmp/test.img", "abc")
        assert ok is False
        assert "Cannot determine disk number" in msg

    @patch("lib.sd_manager_win.os.path.isfile", return_value=False)
    def test_image_not_found(self, mock_isfile):
        ok, msg = write_image_to_device("/nonexistent/image.img", "2")
        assert ok is False
        assert "not found" in msg

    @patch("lib.sd_manager_win._elevate_and_run")
    @patch("lib.sd_manager_win.unmount_all_partitions")
    @patch("lib.sd_manager_win.os.path.getsize", return_value=1024)
    @patch("lib.sd_manager_win.os.path.isfile", return_value=True)
    def test_write_failure(self, mock_isfile, mock_size, mock_unmount, mock_elevate):
        mock_unmount.return_value = (True, "OK")
        mock_elevate.return_value = subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr="Write error occurred",
        )
        ok, msg = write_image_to_device("/tmp/test.img", "2")
        assert ok is False
        assert "Image write failed" in msg

    @patch("lib.sd_manager_win._elevate_and_run")
    @patch("lib.sd_manager_win.unmount_all_partitions")
    @patch("lib.sd_manager_win.os.path.getsize", return_value=1024)
    @patch("lib.sd_manager_win.os.path.isfile", return_value=True)
    def test_write_error_in_stderr(self, mock_isfile, mock_size, mock_unmount, mock_elevate):
        mock_unmount.return_value = (True, "OK")
        mock_elevate.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr="some error message",
        )
        ok, msg = write_image_to_device("/tmp/test.img", "2")
        assert ok is False

    @patch("lib.sd_manager_win._elevate_and_run")
    @patch("lib.sd_manager_win.unmount_all_partitions")
    @patch("lib.sd_manager_win.os.path.getsize", return_value=4096)
    @patch("lib.sd_manager_win.os.path.isfile", return_value=True)
    def test_ps_script_contains_disk_number(self, mock_isfile, mock_size, mock_unmount, mock_elevate):
        mock_unmount.return_value = (True, "OK")
        mock_elevate.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="ok", stderr="",
        )
        write_image_to_device("/tmp/test.img", "3")
        script = mock_elevate.call_args[0][0]
        assert "PhysicalDrive3" in script
        assert "Set-Disk -Number 3" in script

    @patch("lib.sd_manager_win._elevate_and_run")
    @patch("lib.sd_manager_win.unmount_all_partitions")
    @patch("lib.sd_manager_win.os.path.getsize", return_value=1024)
    @patch("lib.sd_manager_win.os.path.isfile", return_value=True)
    def test_custom_timeout(self, mock_isfile, mock_size, mock_unmount, mock_elevate):
        mock_unmount.return_value = (True, "OK")
        mock_elevate.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="ok", stderr="",
        )
        write_image_to_device("/tmp/test.img", "2", timeout=7200)
        assert mock_elevate.call_args.kwargs["timeout"] == 7200


# ---------------------------------------------------------------------------
# Integration: sd_manager.py dispatches to Windows backend
# ---------------------------------------------------------------------------

class TestSdManagerDispatch:
    """Verify sd_manager.py routes to _win functions when IS_WINDOWS is True."""

    @patch("lib.sd_manager.IS_WINDOWS", True)
    @patch("lib.sd_manager._win", create=True)
    def test_list_removable_drives_dispatches(self, mock_win):
        from lib.sd_manager import list_removable_drives as sd_list
        mock_win.list_removable_drives.return_value = [{"name": "Disk1"}]
        result = sd_list()
        mock_win.list_removable_drives.assert_called_once()
        assert result == [{"name": "Disk1"}]

    @patch("lib.sd_manager.IS_WINDOWS", True)
    @patch("lib.sd_manager._win", create=True)
    def test_get_drive_partitions_dispatches(self, mock_win):
        from lib.sd_manager import get_drive_partitions as sd_parts
        mock_win.get_drive_partitions.return_value = [{"name": "E:"}]
        result = sd_parts("2")
        mock_win.get_drive_partitions.assert_called_once_with("2")

    @patch("lib.sd_manager.IS_WINDOWS", True)
    @patch("lib.sd_manager._win", create=True)
    def test_format_sd_card_dispatches(self, mock_win):
        from lib.sd_manager import format_sd_card as sd_fmt
        mock_win.format_sd_card.return_value = (True, "ok")
        ok, msg = sd_fmt("2", "LABEL")
        mock_win.format_sd_card.assert_called_once_with("2", "LABEL", None)

    @patch("lib.sd_manager.IS_WINDOWS", True)
    @patch("lib.sd_manager._win", create=True)
    def test_check_disk_dispatches(self, mock_win):
        from lib.sd_manager import check_disk as sd_chk
        mock_win.check_disk.return_value = "ok"
        result = sd_chk("E:")
        mock_win.check_disk.assert_called_once_with("E:")

    @patch("lib.sd_manager.IS_WINDOWS", True)
    @patch("lib.sd_manager._win", create=True)
    def test_eject_drive_dispatches(self, mock_win):
        from lib.sd_manager import eject_drive as sd_eject
        mock_win.eject_drive.return_value = (True, "ejected")
        ok, msg = sd_eject("2")
        mock_win.eject_drive.assert_called_once_with("2")

    @patch("lib.sd_manager.IS_WINDOWS", True)
    @patch("lib.sd_manager._win", create=True)
    def test_mount_partition_dispatches(self, mock_win):
        from lib.sd_manager import mount_partition as sd_mount
        mock_win.mount_partition.return_value = "E:\\"
        result = sd_mount("E:")
        mock_win.mount_partition.assert_called_once_with("E:")

    @patch("lib.sd_manager.IS_WINDOWS", True)
    @patch("lib.sd_manager._win", create=True)
    def test_unmount_partition_dispatches(self, mock_win):
        from lib.sd_manager import unmount_partition as sd_umount
        mock_win.unmount_partition.return_value = (True, "ok")
        ok, msg = sd_umount("E:")
        mock_win.unmount_partition.assert_called_once_with("E:")

    @patch("lib.sd_manager.IS_WINDOWS", True)
    @patch("lib.sd_manager._win", create=True)
    def test_unmount_all_partitions_dispatches(self, mock_win):
        from lib.sd_manager import unmount_all_partitions as sd_umount_all
        mock_win.unmount_all_partitions.return_value = (True, "ok")
        ok, msg = sd_umount_all("2")
        mock_win.unmount_all_partitions.assert_called_once_with("2")

    @patch("lib.sd_manager.IS_WINDOWS", True)
    @patch("lib.sd_manager._win", create=True)
    def test_write_image_dispatches(self, mock_win):
        from lib.sd_manager import write_image_to_device as sd_write
        mock_win.write_image_to_device.return_value = (True, "ok")
        ok, msg = sd_write("/tmp/img.img", "2", timeout=999)
        mock_win.write_image_to_device.assert_called_once_with("/tmp/img.img", "2", 999)
