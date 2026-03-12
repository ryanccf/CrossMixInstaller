"""Tests for os_profiles.py - OS profile definitions and data integrity."""

import re
import pytest
from lib.os_profiles import OS_PROFILES, SYSTEM_TO_REPO_PATH


# ---------------------------------------------------------------------------
# Required profile keys that every OS profile must have
# ---------------------------------------------------------------------------

REQUIRED_KEYS = [
    "name",
    "device",
    "description",
    "description_source",
    "compatible_devices",
    "install_notes",
    "install_method",
    "releases_url",
    "project_url",
    "wiki_url",
    "sd_label",
    "expected_dirs",
    "detect_markers",
    "version_paths",
    "bios_dir",
    "bios_files",
    "asset_filter",
    "cluster_sectors",
]

VALID_INSTALL_METHODS = {"zip_extract", "raw_image"}


class TestProfileSchema:
    """Verify that every OS profile has the required structure."""

    @pytest.mark.parametrize("profile_key", list(OS_PROFILES.keys()))
    def test_profile_has_all_required_keys(self, profile_key):
        profile = OS_PROFILES[profile_key]
        missing = [k for k in REQUIRED_KEYS if k not in profile]
        assert not missing, f"Profile '{profile_key}' missing keys: {missing}"

    @pytest.mark.parametrize("profile_key", list(OS_PROFILES.keys()))
    def test_profile_name_is_nonempty_string(self, profile_key):
        assert isinstance(OS_PROFILES[profile_key]["name"], str)
        assert len(OS_PROFILES[profile_key]["name"]) > 0

    @pytest.mark.parametrize("profile_key", list(OS_PROFILES.keys()))
    def test_install_method_is_valid(self, profile_key):
        method = OS_PROFILES[profile_key]["install_method"]
        assert method in VALID_INSTALL_METHODS, (
            f"Profile '{profile_key}' has invalid install_method: {method}"
        )

    @pytest.mark.parametrize("profile_key", list(OS_PROFILES.keys()))
    def test_releases_url_is_github_api(self, profile_key):
        url = OS_PROFILES[profile_key]["releases_url"]
        assert url.startswith("https://api.github.com/repos/"), (
            f"Profile '{profile_key}' releases_url doesn't look like a GitHub API URL"
        )
        assert url.endswith("/releases"), (
            f"Profile '{profile_key}' releases_url should end with /releases"
        )

    @pytest.mark.parametrize("profile_key", list(OS_PROFILES.keys()))
    def test_project_url_is_valid(self, profile_key):
        url = OS_PROFILES[profile_key]["project_url"]
        assert url.startswith("https://"), f"Profile '{profile_key}' project_url not HTTPS"

    @pytest.mark.parametrize("profile_key", list(OS_PROFILES.keys()))
    def test_compatible_devices_is_nonempty_list(self, profile_key):
        devices = OS_PROFILES[profile_key]["compatible_devices"]
        assert isinstance(devices, list)
        assert len(devices) > 0, f"Profile '{profile_key}' has no compatible devices"

    @pytest.mark.parametrize("profile_key", list(OS_PROFILES.keys()))
    def test_bios_files_is_list(self, profile_key):
        bios = OS_PROFILES[profile_key]["bios_files"]
        assert isinstance(bios, list)

    @pytest.mark.parametrize("profile_key", list(OS_PROFILES.keys()))
    def test_cluster_sectors_is_callable(self, profile_key):
        fn = OS_PROFILES[profile_key]["cluster_sectors"]
        assert callable(fn), f"Profile '{profile_key}' cluster_sectors is not callable"

    @pytest.mark.parametrize("profile_key", list(OS_PROFILES.keys()))
    def test_cluster_sectors_returns_string(self, profile_key):
        fn = OS_PROFILES[profile_key]["cluster_sectors"]
        result = fn(64 * 1024**3)  # 64 GB
        assert isinstance(result, str), f"cluster_sectors should return str, got {type(result)}"
        assert result.isdigit(), f"cluster_sectors should return a numeric string, got '{result}'"

    @pytest.mark.parametrize("profile_key", list(OS_PROFILES.keys()))
    def test_expected_dirs_is_list_of_strings(self, profile_key):
        dirs = OS_PROFILES[profile_key]["expected_dirs"]
        assert isinstance(dirs, list)
        for d in dirs:
            assert isinstance(d, str)

    @pytest.mark.parametrize("profile_key", list(OS_PROFILES.keys()))
    def test_asset_filter_compiles_if_set(self, profile_key):
        filt = OS_PROFILES[profile_key]["asset_filter"]
        if filt is not None:
            re.compile(filt)  # should not raise


class TestProfileConsistency:
    """Cross-check relationships between profile fields."""

    @pytest.mark.parametrize("profile_key", list(OS_PROFILES.keys()))
    def test_releases_url_matches_project_url(self, profile_key):
        profile = OS_PROFILES[profile_key]
        releases_url = profile["releases_url"]
        project_url = profile["project_url"]
        # Extract owner/repo from both
        api_match = re.search(r"api\.github\.com/repos/([^/]+/[^/]+)/releases", releases_url)
        proj_match = re.search(r"github\.com/([^/]+/[^/]+)", project_url)
        if api_match and proj_match:
            assert api_match.group(1) == proj_match.group(1), (
                f"Profile '{profile_key}': releases_url repo ({api_match.group(1)}) "
                f"doesn't match project_url repo ({proj_match.group(1)})"
            )

    @pytest.mark.parametrize("profile_key", list(OS_PROFILES.keys()))
    def test_wiki_url_is_valid(self, profile_key):
        url = OS_PROFILES[profile_key]["wiki_url"]
        assert url.startswith("https://"), f"Profile '{profile_key}' wiki_url not HTTPS"

    @pytest.mark.parametrize("profile_key", list(OS_PROFILES.keys()))
    def test_raw_image_profiles_have_bios_partition_label(self, profile_key):
        profile = OS_PROFILES[profile_key]
        if profile["install_method"] == "raw_image":
            assert "bios_partition_label" in profile, (
                f"Profile '{profile_key}' uses raw_image install but missing bios_partition_label"
            )

    @pytest.mark.parametrize("profile_key", list(OS_PROFILES.keys()))
    def test_zip_extract_profiles_have_expected_dirs(self, profile_key):
        profile = OS_PROFILES[profile_key]
        if profile["install_method"] == "zip_extract":
            assert len(profile["expected_dirs"]) > 0, (
                f"zip_extract profile '{profile_key}' should have expected_dirs for verification"
            )


class TestBiosFileIntegrity:
    """Verify BIOS file entries across all profiles."""

    @pytest.mark.parametrize("profile_key", list(OS_PROFILES.keys()))
    def test_bios_entries_have_required_keys(self, profile_key):
        bios_keys = {"filename", "system", "md5", "required", "subdir", "extra_copies", "notes"}
        for entry in OS_PROFILES[profile_key]["bios_files"]:
            missing = bios_keys - set(entry.keys())
            assert not missing, (
                f"Profile '{profile_key}', BIOS '{entry.get('filename', '?')}' "
                f"missing keys: {missing}"
            )

    @pytest.mark.parametrize("profile_key", list(OS_PROFILES.keys()))
    def test_bios_systems_in_repo_path_map(self, profile_key):
        for entry in OS_PROFILES[profile_key]["bios_files"]:
            system = entry["system"]
            assert system in SYSTEM_TO_REPO_PATH, (
                f"Profile '{profile_key}': BIOS file '{entry['filename']}' has system "
                f"'{system}' not found in SYSTEM_TO_REPO_PATH"
            )

    @pytest.mark.parametrize("profile_key", list(OS_PROFILES.keys()))
    def test_no_duplicate_bios_filenames(self, profile_key):
        filenames = [e["filename"] for e in OS_PROFILES[profile_key]["bios_files"]]
        seen = set()
        dupes = []
        for f in filenames:
            if f in seen:
                dupes.append(f)
            seen.add(f)
        assert not dupes, (
            f"Profile '{profile_key}' has duplicate BIOS filenames: {dupes}"
        )

    @pytest.mark.parametrize("profile_key", list(OS_PROFILES.keys()))
    def test_md5_hashes_are_valid_hex(self, profile_key):
        for entry in OS_PROFILES[profile_key]["bios_files"]:
            md5 = entry["md5"]
            if md5:  # empty string means "skip verification"
                assert re.fullmatch(r"[0-9a-fA-F]{32}", md5), (
                    f"Profile '{profile_key}': BIOS '{entry['filename']}' "
                    f"has invalid MD5: '{md5}'"
                )

    @pytest.mark.parametrize("profile_key", list(OS_PROFILES.keys()))
    def test_extra_copies_are_strings(self, profile_key):
        for entry in OS_PROFILES[profile_key]["bios_files"]:
            for extra in entry["extra_copies"]:
                assert isinstance(extra, str)
                assert len(extra) > 0

    def test_all_repo_path_systems_are_used(self):
        """Check that every system in SYSTEM_TO_REPO_PATH is referenced by at least one profile."""
        used_systems = set()
        for profile in OS_PROFILES.values():
            for entry in profile["bios_files"]:
                used_systems.add(entry["system"])
        unused = set(SYSTEM_TO_REPO_PATH.keys()) - used_systems
        # This is a warning-level check; unused mappings aren't a bug but are suspicious
        if unused:
            pytest.skip(f"Unused SYSTEM_TO_REPO_PATH entries (not a bug): {unused}")


class TestClusterSectorsLogic:
    """Test cluster_sectors functions for various card sizes."""

    def test_onion_small_card(self):
        fn = OS_PROFILES["onion"]["cluster_sectors"]
        assert fn(32 * 1024**3) == "64"

    def test_onion_large_card(self):
        fn = OS_PROFILES["onion"]["cluster_sectors"]
        assert fn(256 * 1024**3) == "128"

    def test_crossmix_scaling(self):
        fn = OS_PROFILES["crossmix"]["cluster_sectors"]
        assert fn(64 * 1024**3) == "64"
        assert fn(200 * 1024**3) == "128"
        assert fn(300 * 1024**3) == "256"
        assert fn(600 * 1024**3) == "512"
        assert fn(2048 * 1024**3) == "1024"

    @pytest.mark.parametrize("profile_key", list(OS_PROFILES.keys()))
    def test_zero_size_doesnt_crash(self, profile_key):
        fn = OS_PROFILES[profile_key]["cluster_sectors"]
        result = fn(0)
        assert isinstance(result, str)
