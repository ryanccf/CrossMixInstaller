"""Integration tests - end-to-end workflows across modules."""

import hashlib
import zipfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from lib.os_profiles import OS_PROFILES
from lib.bios_manager import (
    _build_download_url,
    download_all_bios,
    install_bios_to_sd,
    scan_cached_bios,
    scan_sd_bios,
)
from lib.os_installer import (
    extract_to_sd,
    verify_extraction,
    get_required_space,
)
from lib.sd_manager import detect_sd_state, get_os_version


# ---------------------------------------------------------------------------
# Full BIOS pipeline: download -> cache -> install -> verify
# ---------------------------------------------------------------------------

class TestBiosPipeline:
    """Test the full BIOS cache -> install -> scan cycle."""

    @patch("lib.bios_manager.download_bios_file")
    def test_download_cache_install_scan(self, mock_dl, tmp_path):
        cache = tmp_path / "cache"
        sd = tmp_path / "sd"

        # Simulate download by creating files in cache
        def fake_download(entry, cache_dir, progress_cb=None):
            dest = cache_dir / entry["filename"]
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(b"\x00" * 16)
            return True, f"Downloaded {entry['filename']}"

        mock_dl.side_effect = fake_download

        entries = [
            {"filename": "test1.bin", "system": "PlayStation", "md5": "",
             "required": True, "subdir": "", "extra_copies": []},
            {"filename": "test2.bin", "system": "GBA", "md5": "",
             "required": False, "subdir": "", "extra_copies": []},
        ]

        # Step 1: Download
        all_ok, succeeded, failed = download_all_bios(cache, entries, skip_cached=False)
        assert all_ok

        # Step 2: Verify cache
        cached = scan_cached_bios(cache, entries)
        assert all(cached.values())

        # Step 3: Install to SD
        all_ok, succeeded, failed = install_bios_to_sd(
            cache, sd, entries, bios_dir="BIOS",
        )
        assert all_ok

        # Step 4: Verify on SD
        sd_scan = scan_sd_bios(sd, entries, bios_dir="BIOS")
        assert all(sd_scan.values())

    @pytest.mark.parametrize("profile_key", list(OS_PROFILES.keys()))
    @patch("lib.bios_manager.download_bios_file")
    def test_install_pipeline_per_profile(self, mock_dl, tmp_path, profile_key):
        """Verify install pipeline works for every profile's bios_dir."""
        profile = OS_PROFILES[profile_key]
        cache = tmp_path / "cache"
        sd = tmp_path / "sd"

        def fake_download(entry, cache_dir, progress_cb=None):
            subdir = entry.get("subdir", "")
            if subdir:
                dest = cache_dir / subdir / entry["filename"]
            else:
                dest = cache_dir / entry["filename"]
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(b"\x00" * 16)
            return True, f"Downloaded {entry['filename']}"

        mock_dl.side_effect = fake_download

        bios_files = profile["bios_files"]
        if not bios_files:
            pytest.skip("No BIOS files for this profile")

        # Download
        all_ok, _, _ = download_all_bios(cache, bios_files, skip_cached=False)
        assert all_ok

        # Install using profile's bios_dir
        bios_dir = profile["bios_dir"]
        all_ok, succeeded, failed = install_bios_to_sd(
            cache, sd, bios_files, bios_dir=bios_dir,
        )
        assert all_ok, f"Failed for {profile_key}: {failed}"

        # Scan
        sd_scan = scan_sd_bios(sd, bios_files, bios_dir=bios_dir)
        assert all(sd_scan.values()), (
            f"Missing on SD for {profile_key}: "
            f"{[k for k, v in sd_scan.items() if not v]}"
        )


# ---------------------------------------------------------------------------
# Full OS install pipeline: extract -> verify -> detect
# ---------------------------------------------------------------------------

class TestOsInstallPipeline:
    def test_extract_and_verify_crossmix(self, tmp_path):
        zip_path = tmp_path / "crossmix.zip"
        sd = tmp_path / "sd"
        sd.mkdir()

        profile = OS_PROFILES["crossmix"]
        with zipfile.ZipFile(zip_path, "w") as zf:
            for d in profile["expected_dirs"]:
                zf.writestr(f"{d}/.gitkeep", "")

        ok, msg = extract_to_sd(zip_path, sd)
        assert ok

        ok, missing = verify_extraction(sd, profile)
        assert ok, f"Missing dirs: {missing}"

    def test_extract_and_verify_onion(self, tmp_path):
        zip_path = tmp_path / "onion.zip"
        sd = tmp_path / "sd"
        sd.mkdir()

        profile = OS_PROFILES["onion"]
        with zipfile.ZipFile(zip_path, "w") as zf:
            for d in profile["expected_dirs"]:
                zf.writestr(f"{d}/.gitkeep", "")

        ok, msg = extract_to_sd(zip_path, sd)
        assert ok

        ok, missing = verify_extraction(sd, profile)
        assert ok, f"Missing dirs: {missing}"

    def test_extract_verify_detect_crossmix(self, tmp_path):
        """Full cycle: extract -> verify -> detect OS state."""
        zip_path = tmp_path / "crossmix.zip"
        sd = tmp_path / "sd"
        sd.mkdir()

        profile = OS_PROFILES["crossmix"]
        with zipfile.ZipFile(zip_path, "w") as zf:
            for d in profile["expected_dirs"]:
                zf.writestr(f"{d}/.gitkeep", "")

        extract_to_sd(zip_path, sd)
        state = detect_sd_state(str(sd))
        assert state == "crossmix"

    def test_extract_verify_detect_onion(self, tmp_path):
        zip_path = tmp_path / "onion.zip"
        sd = tmp_path / "sd"
        sd.mkdir()

        profile = OS_PROFILES["onion"]
        with zipfile.ZipFile(zip_path, "w") as zf:
            for d in profile["expected_dirs"]:
                zf.writestr(f"{d}/.gitkeep", "")

        extract_to_sd(zip_path, sd)
        state = detect_sd_state(str(sd))
        assert state == "onion"


# ---------------------------------------------------------------------------
# Version detection pipeline
# ---------------------------------------------------------------------------

class TestVersionDetection:
    @pytest.mark.parametrize("profile_key,version_content", [
        ("onion", "4.3.1"),
        ("crossmix", "1.3.0"),
        ("koriki", "2.0.0"),
    ])
    def test_version_roundtrip(self, tmp_path, profile_key, version_content):
        """Write a version file and read it back via get_os_version."""
        profile = OS_PROFILES[profile_key]
        version_paths = profile.get("version_paths", [])
        if not version_paths:
            pytest.skip("No version paths")

        # Create the version file at the first path
        version_file = tmp_path / version_paths[0]
        version_file.parent.mkdir(parents=True, exist_ok=True)
        version_file.write_text(version_content + "\n")

        result = get_os_version(str(tmp_path), profile)
        assert result == version_content


# ---------------------------------------------------------------------------
# BIOS URL construction for all profiles
# ---------------------------------------------------------------------------

class TestBiosUrlConstruction:
    @pytest.mark.parametrize("profile_key", list(OS_PROFILES.keys()))
    def test_all_bios_files_have_valid_urls(self, profile_key):
        """Every BIOS entry in every profile should produce a valid download URL."""
        from urllib.parse import quote
        profile = OS_PROFILES[profile_key]
        for entry in profile["bios_files"]:
            url = _build_download_url(entry)
            assert url.startswith("https://"), f"Bad URL for {entry['filename']}: {url}"
            encoded_name = quote(entry["filename"])
            assert encoded_name in url, f"Filename not in URL: {entry['filename']} -> {url}"
