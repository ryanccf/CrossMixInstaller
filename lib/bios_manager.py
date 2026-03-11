"""
bios_manager.py - Download, verify, cache, and install BIOS files.

Works with any OS profile's BIOS file list. Downloads from the
Abdess/retroarch_system GitHub repository, caches locally,
and installs to the SD card's BIOS/ directory.
"""

import hashlib
import logging
import shutil
from pathlib import Path
from typing import Callable, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from lib.os_profiles import SYSTEM_TO_REPO_PATH

logger = logging.getLogger(__name__)

CHUNK_SIZE = 64 * 1024
NETWORK_TIMEOUT = 60

_BASE_RAW_URL = (
    "https://raw.githubusercontent.com/Abdess/retroarch_system/libretro/"
)


def _build_download_url(bios_entry: dict) -> str:
    system = bios_entry["system"]
    repo_path = SYSTEM_TO_REPO_PATH.get(system, "")
    filename = bios_entry["filename"]
    encoded_path = quote(f"{repo_path}{filename}", safe="/")
    return f"{_BASE_RAW_URL}{encoded_path}"


def _cache_path_for(bios_entry: dict, cache_dir: Path) -> Path:
    subdir = bios_entry.get("subdir", "")
    if subdir:
        return cache_dir / subdir / bios_entry["filename"]
    return cache_dir / bios_entry["filename"]


def verify_md5(file_path: Path, expected_md5: str) -> bool:
    """Verify the MD5 checksum of a file.

    Returns True if the checksum matches or if expected_md5 is empty (skip).
    """
    if not expected_md5:
        return True

    md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(CHUNK_SIZE)
            if not chunk:
                break
            md5.update(chunk)

    result = md5.hexdigest() == expected_md5.lower()
    if not result:
        logger.warning(
            "MD5 mismatch for %s: expected %s, got %s",
            file_path.name, expected_md5, md5.hexdigest(),
        )
    return result


def download_bios_file(
    bios_entry: dict,
    cache_dir: Path,
    progress_cb: Optional[Callable[[str, int, int], None]] = None,
) -> tuple[bool, str]:
    """Download a single BIOS file to the cache directory.

    Returns (success, message).
    """
    url = _build_download_url(bios_entry)
    dest = _cache_path_for(bios_entry, cache_dir)
    dest.parent.mkdir(parents=True, exist_ok=True)

    filename = bios_entry["filename"]
    logger.info("Downloading %s from %s", filename, url)

    try:
        request = Request(url)
        with urlopen(request, timeout=NETWORK_TIMEOUT) as response:
            total = int(response.headers.get("Content-Length", 0))
            downloaded = 0

            with open(dest, "wb") as fh:
                while True:
                    chunk = response.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    fh.write(chunk)
                    downloaded += len(chunk)
                    if progress_cb:
                        progress_cb(filename, downloaded, total)

    except HTTPError as exc:
        return False, f"HTTP {exc.code} downloading {filename}: {exc.reason}"
    except URLError as exc:
        return False, f"Network error downloading {filename}: {exc.reason}"
    except TimeoutError:
        return False, f"Timeout downloading {filename}"
    except OSError as exc:
        return False, f"File error saving {filename}: {exc}"

    if not verify_md5(dest, bios_entry.get("md5", "")):
        dest.unlink(missing_ok=True)
        return False, f"MD5 verification failed for {filename}"

    logger.info("Downloaded and verified %s (%d bytes)", filename, downloaded)
    return True, f"Downloaded {filename}"


def scan_cached_bios(cache_dir: Path, bios_files: list[dict]) -> dict[str, bool]:
    """Check which BIOS files exist in the local cache."""
    result = {}
    for entry in bios_files:
        path = _cache_path_for(entry, cache_dir)
        result[entry["filename"]] = path.is_file()
    return result


def scan_sd_bios(sd_mount: Path, bios_files: list[dict], bios_dir: str = "BIOS") -> dict[str, bool]:
    """Check which BIOS files exist on the SD card."""
    bios_dir = sd_mount / bios_dir
    result = {}
    for entry in bios_files:
        subdir = entry.get("subdir", "")
        if subdir:
            path = bios_dir / subdir / entry["filename"]
        else:
            path = bios_dir / entry["filename"]
        result[entry["filename"]] = path.is_file()
    return result


def download_all_bios(
    cache_dir: Path,
    bios_files: list[dict],
    progress_cb: Optional[Callable[[float, str], None]] = None,
    skip_cached: bool = True,
    required_only: bool = False,
) -> tuple[bool, list[str], list[str]]:
    """Download all BIOS files to the cache directory.

    Returns (all_succeeded, succeeded_list, failed_list).
    """
    cache_dir.mkdir(parents=True, exist_ok=True)

    files = [e for e in bios_files if not required_only or e["required"]]
    total = len(files)
    succeeded = []
    failed = []

    for idx, entry in enumerate(files):
        filename = entry["filename"]
        frac = idx / max(total, 1)

        if skip_cached:
            cached_path = _cache_path_for(entry, cache_dir)
            if cached_path.is_file() and verify_md5(cached_path, entry.get("md5", "")):
                if progress_cb:
                    progress_cb(frac, f"Cached: {filename}")
                succeeded.append(filename)
                logger.info("Skipping %s (already cached and verified)", filename)
                continue

        if progress_cb:
            progress_cb(frac, f"Downloading: {filename}")

        ok, msg = download_bios_file(entry, cache_dir)
        if ok:
            succeeded.append(filename)
        else:
            failed.append(f"{filename}: {msg}")
            logger.error("Failed to download %s: %s", filename, msg)

    if progress_cb:
        progress_cb(1.0, "Download complete")

    all_ok = len(failed) == 0
    return all_ok, succeeded, failed


def install_bios_to_sd(
    cache_dir: Path,
    sd_mount: Path,
    bios_files: list[dict],
    progress_cb: Optional[Callable[[float, str], None]] = None,
    required_only: bool = False,
    bios_dir: str = "BIOS",
) -> tuple[bool, list[str], list[str]]:
    """Copy cached BIOS files to the SD card's BIOS/ directory.

    Returns (all_succeeded, succeeded_list, failed_list).
    """
    bios_dir = sd_mount / bios_dir
    bios_dir.mkdir(parents=True, exist_ok=True)

    files = [e for e in bios_files if not required_only or e["required"]]
    total = len(files)
    succeeded = []
    failed = []

    for idx, entry in enumerate(files):
        filename = entry["filename"]
        frac = idx / max(total, 1)

        src = _cache_path_for(entry, cache_dir)
        if not src.is_file():
            failed.append(f"{filename}: not in cache")
            logger.warning("Skipping %s (not in cache)", filename)
            continue

        if progress_cb:
            progress_cb(frac, f"Installing: {filename}")

        try:
            subdir = entry.get("subdir", "")
            if subdir:
                dest_dir = bios_dir / subdir
                dest_dir.mkdir(parents=True, exist_ok=True)
                dest = dest_dir / filename
            else:
                dest = bios_dir / filename

            shutil.copy2(src, dest)
            logger.info("Installed %s -> %s", filename, dest)

            for extra in entry.get("extra_copies", []):
                extra_dest = sd_mount / extra
                extra_dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, extra_dest)
                logger.info("Extra copy %s -> %s", filename, extra_dest)

            succeeded.append(filename)

        except OSError as exc:
            failed.append(f"{filename}: {exc}")
            logger.error("Failed to install %s: %s", filename, exc)

    if progress_cb:
        progress_cb(1.0, "Installation complete")

    all_ok = len(failed) == 0
    return all_ok, succeeded, failed
