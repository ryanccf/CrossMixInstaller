"""
crossmix_installer.py - Download and install CrossMix OS for TrimUI Smart Pro.

Provides functions to fetch releases from GitHub, download release zips,
extract them to an SD card mount point, and verify the installation.
"""

import json
import logging
import os
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)

CROSSMIX_RELEASES_URL = (
    "https://api.github.com/repos/cizia64/CrossMix-OS/releases"
)

NETWORK_TIMEOUT = 30
CHUNK_SIZE = 64 * 1024

# Directories that must be present after a successful CrossMix extraction.
EXPECTED_DIRS = ["System", "Emus", "Apps", "BIOS", "Roms", "RetroArch"]

_GITHUB_HEADERS = {"Accept": "application/vnd.github+json"}


def _github_get(url: str) -> Any:
    request = Request(url, headers=_GITHUB_HEADERS)
    try:
        with urlopen(request, timeout=NETWORK_TIMEOUT) as response:
            data = response.read()
            return json.loads(data)
    except HTTPError as exc:
        raise ConnectionError(
            f"GitHub API returned HTTP {exc.code} for {url}: {exc.reason}"
        ) from exc
    except URLError as exc:
        raise ConnectionError(
            f"Unable to reach {url}: {exc.reason}"
        ) from exc
    except TimeoutError as exc:
        raise ConnectionError(
            f"Request to {url} timed out after {NETWORK_TIMEOUT}s"
        ) from exc


def _find_zip_asset(assets: list[dict]) -> Optional[dict]:
    """Return the first asset whose name ends with .zip, or None."""
    for asset in assets:
        if asset.get("name", "").lower().endswith(".zip"):
            return asset
    return None


def _parse_version(tag: str) -> tuple:
    match = re.search(r"(\d+(?:\.\d+)*)", tag)
    if match:
        return tuple(int(part) for part in match.group(1).split("."))
    return (0,)


def fetch_releases() -> dict[str, list[dict[str, Any]]]:
    """Query the CrossMix OS GitHub releases and return categorised results.

    Returns {"stable": [...], "beta": [...]}
    """
    raw_releases: list[dict] = _github_get(CROSSMIX_RELEASES_URL)

    if not isinstance(raw_releases, list):
        raise ValueError(
            "Unexpected GitHub API response: expected a JSON array of releases"
        )

    stable: list[dict[str, Any]] = []
    beta: list[dict[str, Any]] = []

    for release in raw_releases:
        zip_asset = _find_zip_asset(release.get("assets", []))
        if zip_asset is None:
            continue

        entry: dict[str, Any] = {
            "tag_name": release.get("tag_name", ""),
            "name": release.get("name", ""),
            "prerelease": bool(release.get("prerelease", False)),
            "published_at": release.get("published_at", ""),
            "browser_download_url": zip_asset.get(
                "browser_download_url", ""
            ),
            "size": zip_asset.get("size", 0),
        }

        if entry["prerelease"]:
            beta.append(entry)
        else:
            stable.append(entry)

    return {"stable": stable, "beta": beta}


def download_release(
    url: str,
    dest_dir: str | Path,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> Path:
    """Download a release zip from url into dest_dir.

    Returns the path to the downloaded file.
    """
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    filename = url.rsplit("/", 1)[-1] or "crossmix_release.zip"
    dest_path = dest_dir / filename

    request = Request(url, headers=_GITHUB_HEADERS)

    try:
        with urlopen(request, timeout=NETWORK_TIMEOUT) as response:
            total_bytes = int(response.headers.get("Content-Length", 0))
            bytes_downloaded = 0

            with open(dest_path, "wb") as fh:
                while True:
                    chunk = response.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    fh.write(chunk)
                    bytes_downloaded += len(chunk)
                    if progress_callback is not None:
                        progress_callback(bytes_downloaded, total_bytes)

    except HTTPError as exc:
        raise ConnectionError(
            f"Download failed with HTTP {exc.code}: {exc.reason}"
        ) from exc
    except URLError as exc:
        raise ConnectionError(
            f"Unable to reach download URL {url}: {exc.reason}"
        ) from exc
    except TimeoutError as exc:
        raise ConnectionError(
            f"Download from {url} timed out after {NETWORK_TIMEOUT}s"
        ) from exc

    logger.info("Downloaded %s (%d bytes)", dest_path, bytes_downloaded)
    return dest_path.resolve()


def get_downloaded_releases(
    downloads_dir: str | Path,
) -> list[dict[str, Any]]:
    """List already-downloaded CrossMix OS zip files."""
    downloads_dir = Path(downloads_dir)

    if not downloads_dir.is_dir():
        return []

    results: list[dict[str, Any]] = []
    for entry in downloads_dir.iterdir():
        if entry.is_file() and entry.suffix.lower() == ".zip":
            stat = entry.stat()
            results.append(
                {
                    "filename": entry.name,
                    "path": str(entry.resolve()),
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(
                        stat.st_mtime, tz=timezone.utc
                    ).isoformat(),
                }
            )

    results.sort(key=lambda r: r["modified"], reverse=True)
    return results


def get_required_space(zip_path: str | Path) -> int:
    """Return the total uncompressed size in bytes of a zip archive."""
    zip_path = Path(zip_path)
    with zipfile.ZipFile(zip_path, "r") as zf:
        return sum(info.file_size for info in zf.infolist())


def extract_to_sd(
    zip_path: str | Path,
    sd_mount_point: str | Path,
    progress_callback: Optional[
        Callable[[str, int, int], None]
    ] = None,
) -> tuple[bool, str]:
    """Extract the CrossMix OS zip to an SD card mount point.

    Returns (success, message).
    """
    zip_path = Path(zip_path)
    sd_mount_point = Path(sd_mount_point)

    if not zip_path.is_file():
        return False, f"Zip file not found: {zip_path}"

    if not sd_mount_point.is_dir():
        return False, f"SD card mount point does not exist: {sd_mount_point}"

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            members = zf.infolist()
            total_files = len(members)

            for index, member in enumerate(members):
                target = (sd_mount_point / member.filename).resolve()
                if not str(target).startswith(
                    str(sd_mount_point.resolve())
                ):
                    logger.warning(
                        "Skipping potentially unsafe path: %s",
                        member.filename,
                    )
                    continue

                if progress_callback is not None:
                    progress_callback(member.filename, index, total_files)

                if member.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(member) as src, open(target, "wb") as dst:
                        while True:
                            chunk = src.read(CHUNK_SIZE)
                            if not chunk:
                                break
                            dst.write(chunk)

                    if member.external_attr > 0:
                        unix_mode = member.external_attr >> 16
                        if unix_mode:
                            try:
                                os.chmod(target, unix_mode)
                            except OSError:
                                pass

    except zipfile.BadZipFile as exc:
        return False, f"Invalid zip file: {exc}"
    except OSError as exc:
        return False, f"Extraction error: {exc}"
    except Exception as exc:
        return False, f"Unexpected error during extraction: {exc}"

    return True, "Extraction completed successfully."


def verify_extraction(
    sd_mount_point: str | Path,
) -> tuple[bool, list[str]]:
    """Check that the expected CrossMix OS directories exist on the SD card.

    Returns (success, missing_dirs).
    """
    sd_mount_point = Path(sd_mount_point)
    missing: list[str] = []

    for dirname in EXPECTED_DIRS:
        if not (sd_mount_point / dirname).is_dir():
            missing.append(dirname)

    return (len(missing) == 0, missing)
