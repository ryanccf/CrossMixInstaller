"""Tests for bios_manager.py - BIOS download, verification, caching, and installation."""

import hashlib
from pathlib import Path
from unittest.mock import patch, MagicMock
from urllib.error import HTTPError, URLError

import pytest

from lib.bios_manager import (
    _build_download_url,
    _cache_path_for,
    verify_md5,
    download_bios_file,
    scan_cached_bios,
    scan_sd_bios,
    download_all_bios,
    install_bios_to_sd,
)
from lib.os_profiles import SYSTEM_TO_REPO_PATH


# ---------------------------------------------------------------------------
# URL building
# ---------------------------------------------------------------------------

class TestBuildDownloadUrl:
    def test_basic_url(self):
        entry = {"filename": "scph5501.bin", "system": "PlayStation"}
        url = _build_download_url(entry)
        assert "Sony%20-%20PlayStation/scph5501.bin" in url
        assert url.startswith("https://raw.githubusercontent.com/Abdess/retroarch_system/libretro/")

    def test_url_with_spaces_in_filename(self):
        entry = {"filename": "7800 BIOS (U).rom", "system": "Atari 7800"}
        url = _build_download_url(entry)
        assert "7800%20BIOS%20%28U%29.rom" in url

    def test_unknown_system_uses_empty_prefix(self):
        entry = {"filename": "test.bin", "system": "UnknownSystem"}
        url = _build_download_url(entry)
        assert url.endswith("test.bin")

    @pytest.mark.parametrize("system", list(SYSTEM_TO_REPO_PATH.keys()))
    def test_all_systems_produce_valid_urls(self, system):
        entry = {"filename": "test.bin", "system": system}
        url = _build_download_url(entry)
        assert url.startswith("https://")
        assert "test.bin" in url


# ---------------------------------------------------------------------------
# Cache path
# ---------------------------------------------------------------------------

class TestCachePath:
    def test_flat_file(self, tmp_cache):
        entry = {"filename": "scph5501.bin", "subdir": ""}
        path = _cache_path_for(entry, tmp_cache)
        assert path == tmp_cache / "scph5501.bin"

    def test_subdir_file(self, tmp_cache):
        entry = {"filename": "neocd_f.rom", "subdir": "neocd"}
        path = _cache_path_for(entry, tmp_cache)
        assert path == tmp_cache / "neocd" / "neocd_f.rom"

    def test_missing_subdir_key_defaults_to_flat(self, tmp_cache):
        entry = {"filename": "test.bin"}
        path = _cache_path_for(entry, tmp_cache)
        assert path == tmp_cache / "test.bin"


# ---------------------------------------------------------------------------
# MD5 verification
# ---------------------------------------------------------------------------

class TestVerifyMd5:
    def test_correct_md5(self, tmp_path):
        content = b"hello world"
        f = tmp_path / "test.bin"
        f.write_bytes(content)
        expected = hashlib.md5(content).hexdigest()
        assert verify_md5(f, expected) is True

    def test_incorrect_md5(self, tmp_path):
        f = tmp_path / "test.bin"
        f.write_bytes(b"hello world")
        assert verify_md5(f, "0" * 32) is False

    def test_empty_md5_skips_check(self, tmp_path):
        f = tmp_path / "test.bin"
        f.write_bytes(b"anything")
        assert verify_md5(f, "") is True

    def test_case_insensitive_md5(self, tmp_path):
        content = b"test"
        f = tmp_path / "test.bin"
        f.write_bytes(content)
        expected = hashlib.md5(content).hexdigest().upper()
        assert verify_md5(f, expected) is True


# ---------------------------------------------------------------------------
# Scan cached BIOS
# ---------------------------------------------------------------------------

class TestScanCachedBios:
    def test_empty_cache(self, tmp_cache):
        entries = [
            {"filename": "scph5501.bin", "subdir": ""},
            {"filename": "neogeo.zip", "subdir": ""},
        ]
        result = scan_cached_bios(tmp_cache, entries)
        assert result == {"scph5501.bin": False, "neogeo.zip": False}

    def test_partial_cache(self, tmp_cache, fake_bios_file):
        fake_bios_file("scph5501.bin")
        entries = [
            {"filename": "scph5501.bin", "subdir": ""},
            {"filename": "neogeo.zip", "subdir": ""},
        ]
        result = scan_cached_bios(tmp_cache, entries)
        assert result == {"scph5501.bin": True, "neogeo.zip": False}

    def test_subdir_cache(self, tmp_cache, fake_bios_file):
        fake_bios_file("neocd_f.rom", subdir="neocd")
        entries = [{"filename": "neocd_f.rom", "subdir": "neocd"}]
        result = scan_cached_bios(tmp_cache, entries)
        assert result == {"neocd_f.rom": True}

    def test_empty_bios_list(self, tmp_cache):
        result = scan_cached_bios(tmp_cache, [])
        assert result == {}


# ---------------------------------------------------------------------------
# Scan SD BIOS
# ---------------------------------------------------------------------------

class TestScanSdBios:
    def test_empty_sd(self, tmp_sd):
        entries = [{"filename": "scph5501.bin", "subdir": ""}]
        result = scan_sd_bios(tmp_sd, entries, bios_dir="BIOS")
        assert result == {"scph5501.bin": False}

    def test_file_present_on_sd(self, tmp_sd):
        bios_dir = tmp_sd / "BIOS"
        bios_dir.mkdir()
        (bios_dir / "scph5501.bin").write_bytes(b"\x00")
        entries = [{"filename": "scph5501.bin", "subdir": ""}]
        result = scan_sd_bios(tmp_sd, entries, bios_dir="BIOS")
        assert result == {"scph5501.bin": True}

    def test_custom_bios_dir(self, tmp_sd):
        bios_dir = tmp_sd / "roms" / "bios"
        bios_dir.mkdir(parents=True)
        (bios_dir / "scph5501.bin").write_bytes(b"\x00")
        entries = [{"filename": "scph5501.bin", "subdir": ""}]
        result = scan_sd_bios(tmp_sd, entries, bios_dir="roms/bios")
        assert result == {"scph5501.bin": True}

    def test_subdir_on_sd(self, tmp_sd):
        neocd_dir = tmp_sd / "BIOS" / "neocd"
        neocd_dir.mkdir(parents=True)
        (neocd_dir / "neocd_f.rom").write_bytes(b"\x00")
        entries = [{"filename": "neocd_f.rom", "subdir": "neocd"}]
        result = scan_sd_bios(tmp_sd, entries, bios_dir="BIOS")
        assert result == {"neocd_f.rom": True}


# ---------------------------------------------------------------------------
# Download BIOS file (mocked network)
# ---------------------------------------------------------------------------

class TestDownloadBiosFile:
    @patch("lib.bios_manager.urlopen")
    def test_successful_download(self, mock_urlopen, tmp_cache):
        content = b"fake bios data"
        mock_response = MagicMock()
        mock_response.read.side_effect = [content, b""]
        mock_response.headers = {"Content-Length": str(len(content))}
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        entry = {
            "filename": "test.bin",
            "system": "PlayStation",
            "md5": "",
            "subdir": "",
        }
        ok, msg = download_bios_file(entry, tmp_cache)
        assert ok is True
        assert "Downloaded" in msg
        assert (tmp_cache / "test.bin").is_file()

    @patch("lib.bios_manager.urlopen")
    def test_http_error(self, mock_urlopen, tmp_cache):
        mock_urlopen.side_effect = HTTPError(
            url="http://example.com", code=404, msg="Not Found",
            hdrs=None, fp=None,
        )
        entry = {
            "filename": "missing.bin",
            "system": "PlayStation",
            "md5": "",
            "subdir": "",
        }
        ok, msg = download_bios_file(entry, tmp_cache)
        assert ok is False
        assert "404" in msg

    @patch("lib.bios_manager.urlopen")
    def test_url_error(self, mock_urlopen, tmp_cache):
        mock_urlopen.side_effect = URLError("Connection refused")
        entry = {
            "filename": "test.bin",
            "system": "PlayStation",
            "md5": "",
            "subdir": "",
        }
        ok, msg = download_bios_file(entry, tmp_cache)
        assert ok is False
        assert "Network error" in msg

    @patch("lib.bios_manager.urlopen")
    def test_timeout_error(self, mock_urlopen, tmp_cache):
        mock_urlopen.side_effect = TimeoutError()
        entry = {
            "filename": "test.bin",
            "system": "PlayStation",
            "md5": "",
            "subdir": "",
        }
        ok, msg = download_bios_file(entry, tmp_cache)
        assert ok is False
        assert "Timeout" in msg

    @patch("lib.bios_manager.urlopen")
    def test_md5_mismatch_deletes_file(self, mock_urlopen, tmp_cache):
        content = b"wrong content"
        mock_response = MagicMock()
        mock_response.read.side_effect = [content, b""]
        mock_response.headers = {"Content-Length": str(len(content))}
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        entry = {
            "filename": "test.bin",
            "system": "PlayStation",
            "md5": "0" * 32,
            "subdir": "",
        }
        ok, msg = download_bios_file(entry, tmp_cache)
        assert ok is False
        assert "MD5" in msg
        assert not (tmp_cache / "test.bin").exists()

    @patch("lib.bios_manager.urlopen")
    def test_progress_callback_called(self, mock_urlopen, tmp_cache):
        content = b"data"
        mock_response = MagicMock()
        mock_response.read.side_effect = [content, b""]
        mock_response.headers = {"Content-Length": str(len(content))}
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        cb = MagicMock()
        entry = {
            "filename": "test.bin",
            "system": "PlayStation",
            "md5": "",
            "subdir": "",
        }
        download_bios_file(entry, tmp_cache, progress_cb=cb)
        cb.assert_called()


# ---------------------------------------------------------------------------
# Download all BIOS (mocked)
# ---------------------------------------------------------------------------

class TestDownloadAllBios:
    @patch("lib.bios_manager.download_bios_file")
    def test_all_succeed(self, mock_dl, tmp_cache):
        mock_dl.return_value = (True, "ok")
        entries = [
            {"filename": "a.bin", "system": "PlayStation", "md5": "", "required": True, "subdir": ""},
            {"filename": "b.bin", "system": "PlayStation", "md5": "", "required": True, "subdir": ""},
        ]
        all_ok, succeeded, failed = download_all_bios(tmp_cache, entries, skip_cached=False)
        assert all_ok is True
        assert len(succeeded) == 2
        assert len(failed) == 0

    @patch("lib.bios_manager.download_bios_file")
    def test_partial_failure(self, mock_dl, tmp_cache):
        mock_dl.side_effect = [
            (True, "ok"),
            (False, "HTTP 404"),
        ]
        entries = [
            {"filename": "a.bin", "system": "PlayStation", "md5": "", "required": True, "subdir": ""},
            {"filename": "b.bin", "system": "PlayStation", "md5": "", "required": True, "subdir": ""},
        ]
        all_ok, succeeded, failed = download_all_bios(tmp_cache, entries, skip_cached=False)
        assert all_ok is False
        assert len(succeeded) == 1
        assert len(failed) == 1

    @patch("lib.bios_manager.download_bios_file")
    def test_required_only_filter(self, mock_dl, tmp_cache):
        mock_dl.return_value = (True, "ok")
        entries = [
            {"filename": "a.bin", "system": "PlayStation", "md5": "", "required": True, "subdir": ""},
            {"filename": "b.bin", "system": "GBA", "md5": "", "required": False, "subdir": ""},
        ]
        all_ok, succeeded, failed = download_all_bios(
            tmp_cache, entries, skip_cached=False, required_only=True,
        )
        assert all_ok is True
        assert len(succeeded) == 1
        assert succeeded == ["a.bin"]
        assert mock_dl.call_count == 1

    def test_skip_cached_with_verified_file(self, tmp_cache, fake_bios_file):
        content = b"known content"
        md5 = hashlib.md5(content).hexdigest()
        fake_bios_file("a.bin", content=content)
        entries = [
            {"filename": "a.bin", "system": "PlayStation", "md5": md5, "required": True, "subdir": ""},
        ]
        all_ok, succeeded, failed = download_all_bios(tmp_cache, entries, skip_cached=True)
        assert all_ok is True
        assert "a.bin" in succeeded

    def test_empty_bios_list(self, tmp_cache):
        all_ok, succeeded, failed = download_all_bios(tmp_cache, [])
        assert all_ok is True
        assert succeeded == []
        assert failed == []

    @patch("lib.bios_manager.download_bios_file")
    def test_progress_callback(self, mock_dl, tmp_cache):
        mock_dl.return_value = (True, "ok")
        entries = [
            {"filename": "a.bin", "system": "PlayStation", "md5": "", "required": True, "subdir": ""},
        ]
        cb = MagicMock()
        download_all_bios(tmp_cache, entries, progress_cb=cb, skip_cached=False)
        assert cb.call_count >= 2  # at least one progress + final


# ---------------------------------------------------------------------------
# Install BIOS to SD
# ---------------------------------------------------------------------------

class TestInstallBiosToSd:
    def test_install_flat_file(self, tmp_cache, tmp_sd, fake_bios_file):
        fake_bios_file("scph5501.bin")
        entries = [
            {"filename": "scph5501.bin", "system": "PlayStation", "md5": "",
             "required": True, "subdir": "", "extra_copies": []},
        ]
        all_ok, succeeded, failed = install_bios_to_sd(
            tmp_cache, tmp_sd, entries, bios_dir="BIOS",
        )
        assert all_ok is True
        assert (tmp_sd / "BIOS" / "scph5501.bin").is_file()

    def test_install_subdir_file(self, tmp_cache, tmp_sd, fake_bios_file):
        fake_bios_file("neocd_f.rom", subdir="neocd")
        entries = [
            {"filename": "neocd_f.rom", "system": "Neo Geo CD", "md5": "",
             "required": False, "subdir": "neocd", "extra_copies": []},
        ]
        all_ok, succeeded, failed = install_bios_to_sd(
            tmp_cache, tmp_sd, entries, bios_dir="BIOS",
        )
        assert all_ok is True
        assert (tmp_sd / "BIOS" / "neocd" / "neocd_f.rom").is_file()

    def test_install_with_extra_copies(self, tmp_cache, tmp_sd, fake_bios_file):
        fake_bios_file("neogeo.zip")
        entries = [
            {"filename": "neogeo.zip", "system": "Neo Geo", "md5": "",
             "required": True, "subdir": "", "extra_copies": ["Roms/NEOGEO/neogeo.zip"]},
        ]
        all_ok, succeeded, failed = install_bios_to_sd(
            tmp_cache, tmp_sd, entries, bios_dir="BIOS",
        )
        assert all_ok is True
        assert (tmp_sd / "BIOS" / "neogeo.zip").is_file()
        assert (tmp_sd / "Roms" / "NEOGEO" / "neogeo.zip").is_file()

    def test_missing_from_cache(self, tmp_cache, tmp_sd):
        entries = [
            {"filename": "missing.bin", "system": "PlayStation", "md5": "",
             "required": True, "subdir": "", "extra_copies": []},
        ]
        all_ok, succeeded, failed = install_bios_to_sd(
            tmp_cache, tmp_sd, entries, bios_dir="BIOS",
        )
        assert all_ok is False
        assert len(failed) == 1
        assert "not in cache" in failed[0]

    def test_custom_bios_dir(self, tmp_cache, tmp_sd, fake_bios_file):
        fake_bios_file("scph5501.bin")
        entries = [
            {"filename": "scph5501.bin", "system": "PlayStation", "md5": "",
             "required": True, "subdir": "", "extra_copies": []},
        ]
        all_ok, succeeded, failed = install_bios_to_sd(
            tmp_cache, tmp_sd, entries, bios_dir="roms/bios",
        )
        assert all_ok is True
        assert (tmp_sd / "roms" / "bios" / "scph5501.bin").is_file()

    def test_creates_bios_dir_if_missing(self, tmp_cache, tmp_sd, fake_bios_file):
        fake_bios_file("test.bin")
        entries = [
            {"filename": "test.bin", "system": "PlayStation", "md5": "",
             "required": True, "subdir": "", "extra_copies": []},
        ]
        all_ok, _, _ = install_bios_to_sd(tmp_cache, tmp_sd, entries, bios_dir="BIOS")
        assert (tmp_sd / "BIOS").is_dir()

    def test_progress_callback(self, tmp_cache, tmp_sd, fake_bios_file):
        fake_bios_file("test.bin")
        entries = [
            {"filename": "test.bin", "system": "PlayStation", "md5": "",
             "required": True, "subdir": "", "extra_copies": []},
        ]
        cb = MagicMock()
        install_bios_to_sd(tmp_cache, tmp_sd, entries, progress_cb=cb, bios_dir="BIOS")
        assert cb.call_count >= 2

    def test_required_only_filter(self, tmp_cache, tmp_sd, fake_bios_file):
        fake_bios_file("req.bin")
        fake_bios_file("opt.bin")
        entries = [
            {"filename": "req.bin", "system": "PlayStation", "md5": "",
             "required": True, "subdir": "", "extra_copies": []},
            {"filename": "opt.bin", "system": "GBA", "md5": "",
             "required": False, "subdir": "", "extra_copies": []},
        ]
        all_ok, succeeded, failed = install_bios_to_sd(
            tmp_cache, tmp_sd, entries, bios_dir="BIOS", required_only=True,
        )
        assert all_ok is True
        assert succeeded == ["req.bin"]
        assert (tmp_sd / "BIOS" / "req.bin").is_file()
        assert not (tmp_sd / "BIOS" / "opt.bin").exists()
