"""
sd_manager.py - SD card operations for CrossMix OS installer.

Manages SD card detection, mounting, formatting, and validation
for the TrimUI Smart Pro using native Linux tools.
"""

import json
import logging
import os
import shutil
import subprocess

logger = logging.getLogger(__name__)

_TOOL_PATHS = {
    "parted": "/sbin/parted",
    "mkfs.vfat": "/sbin/mkfs.vfat",
    "fsck.vfat": "/sbin/fsck.vfat",
    "partprobe": "/sbin/partprobe",
}


def _tool(name: str) -> str:
    path = _TOOL_PATHS.get(name, name)
    if os.path.isfile(path):
        return path
    return shutil.which(name) or name


def _is_root() -> bool:
    return os.geteuid() == 0


def _run(cmd: list[str], *, check: bool = False,
         timeout: int = 120) -> subprocess.CompletedProcess:
    logger.debug("Running: %s", " ".join(cmd))
    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=timeout,
    )
    if result.returncode != 0:
        logger.debug("stderr: %s", result.stderr.strip())
    if check:
        result.check_returncode()
    return result


def _privileged_run(cmd: list[str], *, check: bool = False,
                    timeout: int = 120) -> subprocess.CompletedProcess:
    if _is_root():
        return _run(cmd, check=check, timeout=timeout)
    return _run(["pkexec"] + cmd, check=check, timeout=timeout)


def _device_basename(device: str) -> str:
    return os.path.basename(device)


def _ensure_block_device(device: str) -> str:
    if not device.startswith("/dev/"):
        device = f"/dev/{device}"
    return device


def _card_size_bytes(device: str) -> int:
    name = _device_basename(device)
    try:
        with open(f"/sys/block/{name}/size") as fh:
            sectors = int(fh.read().strip())
        return sectors * 512
    except (FileNotFoundError, ValueError, OSError):
        return 0


def list_removable_drives() -> list[dict]:
    """Enumerate removable drives visible to the system."""
    result = _run([
        "lsblk", "-J", "-o",
        "NAME,SIZE,TYPE,MOUNTPOINT,FSTYPE,RM,MODEL,TRAN,LABEL",
    ])
    if result.returncode != 0:
        logger.error("lsblk failed: %s", result.stderr.strip())
        return []

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        logger.error("Failed to parse lsblk JSON output")
        return []

    drives: list[dict] = []
    for dev in data.get("blockdevices", []):
        rm = dev.get("rm")
        if isinstance(rm, str):
            rm = rm.strip() == "1"
        elif isinstance(rm, (int, float)):
            rm = bool(rm)
        else:
            rm = False

        if not rm:
            continue
        if dev.get("type") != "disk":
            continue

        drive_info = {
            "name": dev.get("name", ""),
            "device": f"/dev/{dev.get('name', '')}",
            "size": dev.get("size", ""),
            "type": dev.get("type", ""),
            "mountpoint": dev.get("mountpoint"),
            "fstype": dev.get("fstype"),
            "rm": True,
            "model": (dev.get("model") or "").strip(),
            "tran": dev.get("tran"),
            "label": dev.get("label"),
            "children": dev.get("children", []),
        }
        drives.append(drive_info)

    return drives


def get_drive_partitions(device: str) -> list[dict]:
    """Return a list of partitions for a device."""
    device = _ensure_block_device(device)

    result = _run([
        "lsblk", "-J", "-o",
        "NAME,SIZE,TYPE,MOUNTPOINT,FSTYPE,LABEL",
        device,
    ])
    if result.returncode != 0:
        logger.error("lsblk failed for %s: %s", device, result.stderr.strip())
        return []

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        logger.error("Failed to parse lsblk JSON output for %s", device)
        return []

    partitions: list[dict] = []
    for dev in data.get("blockdevices", []):
        for child in dev.get("children", []):
            if child.get("type") == "part":
                partitions.append({
                    "name": child.get("name", ""),
                    "device": f"/dev/{child.get('name', '')}",
                    "size": child.get("size", ""),
                    "mountpoint": child.get("mountpoint"),
                    "fstype": child.get("fstype"),
                    "label": child.get("label"),
                })
    return partitions


def detect_sd_state(mount_point: str) -> str:
    """Determine what is currently on the SD card.

    Returns "onion", "crossmix", "stock", "empty", or "unknown".
    """
    if not os.path.isdir(mount_point):
        return "unknown"

    try:
        entries = os.listdir(mount_point)
    except OSError:
        return "unknown"

    meaningful = [
        e for e in entries
        if e not in {"System Volume Information", ".Trash-1000",
                     "$RECYCLE.BIN", ".fseventsd", ".Spotlight-V100"}
    ]

    if not meaningful:
        return "empty"

    if ".tmp_update" in entries:
        return "onion"

    if "System" in entries and "Emus" in entries:
        return "crossmix"

    if "miyoo" in entries:
        return "stock"

    return "unknown"


def get_os_version(mount_point: str, profile: dict) -> str | None:
    """Read the installed OS version from the SD card using the profile's version paths."""
    for rel_path in profile.get("version_paths", []):
        version_file = os.path.join(mount_point, rel_path)
        try:
            with open(version_file) as fh:
                return fh.read().strip()
        except (FileNotFoundError, OSError):
            continue
    return None


def _partition_device_for(device: str) -> str:
    base = _device_basename(device)
    if base[-1].isdigit():
        return f"{device}p1"
    return f"{device}1"


def format_sd_card(device: str, label: str = "SDCARD",
                   cluster_sectors_fn=None) -> tuple[bool, str]:
    """Format device as FAT32 with an MBR partition table.

    Parameters
    ----------
    label : str
        Volume label (max 11 ASCII characters).
    cluster_sectors_fn : callable, optional
        Function that takes size_bytes and returns cluster sectors string.
        Defaults to "64" if not provided.
    """
    device = _ensure_block_device(device)
    label = label[:11].upper()

    partition_device = _partition_device_for(device)

    size_bytes = _card_size_bytes(device)
    if cluster_sectors_fn:
        cluster_sectors = cluster_sectors_fn(size_bytes)
    else:
        cluster_sectors = "64"

    # Unmount via udisksctl first
    partitions = get_drive_partitions(device)
    for part in partitions:
        if part.get("mountpoint"):
            _run(["udisksctl", "unmount", "-b", part["device"]])

    script = f"""#!/bin/sh
set -e

for p in {device}*; do
    umount "$p" 2>/dev/null || true
done

{_tool("parted")} -s {device} mklabel msdos
{_tool("parted")} -s -a optimal {device} mkpart primary fat32 1MiB 100%
{_tool("partprobe")} {device}
udevadm settle --timeout=5
sleep 1

{_tool("mkfs.vfat")} -F32 -s {cluster_sectors} -n {label} {partition_device}

udevadm settle --timeout=5
"""

    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
        f.write(script)
        script_path = f.name

    try:
        os.chmod(script_path, 0o755)
        res = _privileged_run([script_path], timeout=300)
        if res.returncode != 0:
            error = res.stderr.strip() or res.stdout.strip()
            return False, f"Format failed: {error}"
    finally:
        try:
            os.unlink(script_path)
        except OSError:
            pass

    return True, f"Successfully formatted {device} as FAT32 (label={label})"


def check_disk(device: str) -> str:
    """Run a non-destructive filesystem check on the first partition."""
    device = _ensure_block_device(device)
    partition_device = _partition_device_for(device)

    partitions = get_drive_partitions(device)
    for part in partitions:
        if part.get("mountpoint") and part["device"] == partition_device:
            _run(["udisksctl", "unmount", "-b", partition_device])

    res = _privileged_run([_tool("fsck.vfat"), "-n", partition_device], timeout=300)
    output = (res.stdout + "\n" + res.stderr).strip()
    return output


def eject_drive(device: str) -> tuple[bool, str]:
    """Safely eject a device (unmount + power-off)."""
    device = _ensure_block_device(device)

    partitions = get_drive_partitions(device)
    for part in partitions:
        if part.get("mountpoint"):
            res = _run(["udisksctl", "unmount", "-b", part["device"]])
            if res.returncode != 0:
                res = _privileged_run(["umount", part["device"]])
                if res.returncode != 0:
                    return False, f"Failed to unmount {part['device']}: {res.stderr.strip()}"

    res = _run(["udisksctl", "power-off", "-b", device])
    if res.returncode == 0:
        return True, f"Drive {device} has been safely ejected."

    if shutil.which("eject"):
        res = _privileged_run(["eject", device])
        if res.returncode == 0:
            return True, f"Drive {device} has been ejected (via eject)."
        return False, f"Failed to eject {device}: {res.stderr.strip()}"

    return False, f"Failed to power-off {device}: {res.stderr.strip()}"


def mount_partition(partition: str) -> str | None:
    """Mount a partition via udisksctl and return the mount point."""
    partition = _ensure_block_device(partition)

    res = _run(["udisksctl", "mount", "-b", partition])
    if res.returncode != 0:
        logger.error("mount failed for %s: %s", partition, res.stderr.strip())
        return None

    stdout = res.stdout.strip()
    if " at " in stdout:
        mount_point = stdout.split(" at ", 1)[1].rstrip(".")
        return mount_point

    info = _run(["lsblk", "-n", "-o", "MOUNTPOINT", partition])
    mp = info.stdout.strip()
    return mp if mp else None


def unmount_partition(partition: str) -> tuple[bool, str]:
    """Unmount a partition."""
    partition = _ensure_block_device(partition)

    res = _run(["udisksctl", "unmount", "-b", partition])
    if res.returncode == 0:
        return True, f"Unmounted {partition}."

    res = _privileged_run(["umount", partition])
    if res.returncode == 0:
        return True, f"Unmounted {partition} (via umount)."

    return False, f"Failed to unmount {partition}: {res.stderr.strip()}"


def get_free_space(path: str) -> int:
    """Return the free space in bytes available at a path."""
    try:
        st = os.statvfs(path)
        return st.f_bavail * st.f_frsize
    except OSError:
        return 0


def unmount_all_partitions(device: str) -> tuple[bool, str]:
    """Unmount all mounted partitions on a device."""
    device = _ensure_block_device(device)
    partitions = get_drive_partitions(_device_basename(device))
    failed = []
    for part in partitions:
        if part.get("mountpoint"):
            res = _run(["udisksctl", "unmount", "-b", part["device"]])
            if res.returncode != 0:
                res = _privileged_run(["umount", part["device"]])
                if res.returncode != 0:
                    failed.append(part["device"])
    if failed:
        return False, f"Failed to unmount: {', '.join(failed)}"
    return True, "All partitions unmounted."


def write_image_to_device(
    img_path: str,
    device: str,
    timeout: int = 3600,
) -> tuple[bool, str]:
    """Write a raw .img file to a block device using dd.

    Unmounts all partitions first, then writes with dd via pkexec.
    Returns (success, message).
    """
    device = _ensure_block_device(device)

    import tempfile
    script = f"""#!/bin/sh
set -e

# Unmount all partitions
for p in {device}*; do
    umount "$p" 2>/dev/null || true
done

# Write image
dd if={img_path} of={device} bs=4M conv=fsync status=progress 2>&1

sync
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
        f.write(script)
        script_path = f.name

    try:
        os.chmod(script_path, 0o755)
        res = _privileged_run([script_path], timeout=timeout)
        if res.returncode != 0:
            error = res.stderr.strip() or res.stdout.strip()
            return False, f"Image write failed: {error}"
    finally:
        try:
            os.unlink(script_path)
        except OSError:
            pass

    return True, f"Image written successfully to {device}."
