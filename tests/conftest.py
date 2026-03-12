"""Shared fixtures for CrossMixInstaller tests."""

import pytest
from pathlib import Path


@pytest.fixture
def tmp_cache(tmp_path):
    """Return a temporary BIOS cache directory."""
    cache = tmp_path / "bios_cache"
    cache.mkdir()
    return cache


@pytest.fixture
def tmp_sd(tmp_path):
    """Return a temporary SD card mount point."""
    sd = tmp_path / "sd"
    sd.mkdir()
    return sd


@pytest.fixture
def fake_bios_file(tmp_cache):
    """Create a fake BIOS file in the cache and return its path."""
    def _create(filename, content=b"\x00" * 256, subdir=""):
        if subdir:
            dest = tmp_cache / subdir / filename
        else:
            dest = tmp_cache / filename
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(content)
        return dest
    return _create


@pytest.fixture
def sample_bios_entry():
    """Return a sample BIOS entry dict."""
    return {
        "filename": "scph5501.bin",
        "system": "PlayStation",
        "md5": "490f666e1afb15b7362b406ed1cea246",
        "required": True,
        "subdir": "",
        "extra_copies": [],
        "notes": "PS1 BIOS (North America)",
    }


@pytest.fixture
def sample_bios_entry_with_subdir():
    """Return a sample BIOS entry with subdir."""
    return {
        "filename": "neocd_f.rom",
        "system": "Neo Geo CD",
        "md5": "",
        "required": False,
        "subdir": "neocd",
        "extra_copies": [],
        "notes": "Neo Geo CD front loader BIOS",
    }


@pytest.fixture
def sample_bios_entry_with_extra_copies():
    """Return a sample BIOS entry with extra_copies."""
    return {
        "filename": "neogeo.zip",
        "system": "Neo Geo",
        "md5": "",
        "required": True,
        "subdir": "",
        "extra_copies": ["Roms/NEOGEO/neogeo.zip"],
        "notes": "Neo Geo BIOS (also needed in Roms/NEOGEO/)",
    }
