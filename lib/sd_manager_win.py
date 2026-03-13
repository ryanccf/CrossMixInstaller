"""
sd_manager_win.py - Windows SD card operations.

Uses PowerShell and direct disk I/O for SD card management on Windows.
All functions match the signatures expected by sd_manager.py.
"""

import ctypes
import json
import logging
import os
import re
import shutil
import subprocess
import tempfile

logger = logging.getLogger(__name__)

_SAFE_LABEL_RE = re.compile(r"^[A-Z0-9_ ]{0,11}$")


def _ps(script: str, *, timeout: int = 120) -> subprocess.CompletedProcess:
    """Run a PowerShell script and return the result."""
    return subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True, text=True, timeout=timeout,
    )


def _ps_json(script: str, *, timeout: int = 120):
    """Run a PowerShell script that outputs JSON and parse the result."""
    result = _ps(f"{script} | ConvertTo-Json -Depth 5", timeout=timeout)
    if result.returncode != 0:
        logger.error("PowerShell error: %s", result.stderr.strip())
        return None
    text = result.stdout.strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        logger.error("Failed to parse PowerShell JSON: %s", text[:200])
        return None


def _is_admin() -> bool:
    """Check if the current process has administrator privileges."""
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def _elevate_and_run(script: str, *, timeout: int = 300) -> subprocess.CompletedProcess:
    """Run a PowerShell script with UAC elevation if needed."""
    if _is_admin():
        return _ps(script, timeout=timeout)

    # Write script to temp file and run elevated
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".ps1", delete=False, dir=tempfile.gettempdir()
    ) as f:
        # Wrap script to write output/errors to temp files we can read back
        out_file = f.name + ".out"
        err_file = f.name + ".err"
        f.write(f"""
try {{
    {script}
}} | Out-File -FilePath '{out_file}' -Encoding utf8
$error | Out-File -FilePath '{err_file}' -Encoding utf8
""")
        script_path = f.name

    try:
        # ShellExecuteW with "runas" triggers UAC prompt
        ret = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", "powershell.exe",
            f'-NoProfile -ExecutionPolicy Bypass -File "{script_path}"',
            None, 0,  # SW_HIDE
        )
        if ret <= 32:
            return subprocess.CompletedProcess(
                args=["powershell"], returncode=1,
                stdout="", stderr="UAC elevation was denied or failed.",
            )

        # Wait for the elevated process to finish
        import time
        for _ in range(timeout):
            if os.path.exists(out_file) or os.path.exists(err_file):
                time.sleep(1)  # Give it a moment to finish writing
                break
            time.sleep(1)
        else:
            return subprocess.CompletedProcess(
                args=["powershell"], returncode=1,
                stdout="", stderr="Elevated operation timed out.",
            )

        stdout = ""
        stderr = ""
        if os.path.exists(out_file):
            stdout = open(out_file, encoding="utf-8", errors="replace").read()
        if os.path.exists(err_file):
            stderr = open(err_file, encoding="utf-8", errors="replace").read()

        return subprocess.CompletedProcess(
            args=["powershell"], returncode=0,
            stdout=stdout, stderr=stderr,
        )
    finally:
        for p in (script_path, out_file, err_file):
            try:
                os.unlink(p)
            except OSError:
                pass


def _disk_number_from_device(device: str) -> int | None:
    """Extract disk number from a Windows device identifier.

    Accepts: "2", "\\\\?\\PhysicalDrive2", "PhysicalDrive2", or a dict-like
    device name from list_removable_drives.
    """
    m = re.search(r"(\d+)$", str(device))
    return int(m.group(1)) if m else None


def list_removable_drives() -> list[dict]:
    """Enumerate removable USB/SD drives on Windows."""
    data = _ps_json(
        "Get-Disk | Where-Object { $_.BusType -eq 'USB' -or $_.BusType -eq 'SD' } "
        "| Select-Object Number, FriendlyName, Size, BusType, PartitionStyle"
    )
    if data is None:
        return []

    # PowerShell returns a single object (not array) when there's one result
    if isinstance(data, dict):
        data = [data]

    drives = []
    for disk in data:
        disk_num = disk.get("Number")
        size_bytes = disk.get("Size", 0)

        # Get human-readable size
        if size_bytes >= 1024**3:
            size_str = f"{size_bytes / 1024**3:.1f}G"
        elif size_bytes >= 1024**2:
            size_str = f"{size_bytes / 1024**2:.0f}M"
        else:
            size_str = f"{size_bytes}"

        # Get partition/volume info for labels and mount points
        parts = _ps_json(
            f"Get-Partition -DiskNumber {disk_num} -ErrorAction SilentlyContinue "
            f"| Select-Object PartitionNumber, DriveLetter, Size, Type"
        )
        if isinstance(parts, dict):
            parts = [parts]

        label = None
        mountpoint = None
        children = []
        if parts:
            for part in parts:
                dl = part.get("DriveLetter")
                if dl and str(dl).strip():
                    drive_letter = f"{dl}:"
                    mountpoint = f"{drive_letter}\\"
                    # Get volume label
                    vol = _ps_json(
                        f"Get-Volume -DriveLetter '{dl}' -ErrorAction SilentlyContinue "
                        f"| Select-Object FileSystemLabel, FileSystem, SizeRemaining"
                    )
                    if isinstance(vol, dict):
                        label = vol.get("FileSystemLabel") or None
                    children.append({
                        "name": drive_letter,
                        "device": drive_letter,
                        "size": size_str,
                        "mountpoint": mountpoint,
                        "fstype": vol.get("FileSystem") if isinstance(vol, dict) else None,
                        "label": label,
                    })

        drives.append({
            "name": f"Disk{disk_num}",
            "device": f"\\\\.\\PhysicalDrive{disk_num}",
            "size": size_str,
            "type": "disk",
            "mountpoint": mountpoint,
            "fstype": None,
            "rm": True,
            "model": (disk.get("FriendlyName") or "").strip(),
            "tran": (disk.get("BusType") or "").strip(),
            "label": label,
            "children": children,
        })

    return drives


def get_drive_partitions(device: str) -> list[dict]:
    """Return partitions for a disk identified by number or device path."""
    disk_num = _disk_number_from_device(device)
    if disk_num is None:
        return []

    parts = _ps_json(
        f"Get-Partition -DiskNumber {disk_num} -ErrorAction SilentlyContinue "
        f"| Select-Object PartitionNumber, DriveLetter, Size, Type"
    )
    if parts is None:
        return []
    if isinstance(parts, dict):
        parts = [parts]

    result = []
    for part in parts:
        dl = part.get("DriveLetter")
        drive_letter = f"{dl}:" if dl and str(dl).strip() else None

        label = None
        fstype = None
        mountpoint = None
        if drive_letter:
            mountpoint = f"{drive_letter}\\"
            vol = _ps_json(
                f"Get-Volume -DriveLetter '{dl}' -ErrorAction SilentlyContinue "
                f"| Select-Object FileSystemLabel, FileSystem"
            )
            if isinstance(vol, dict):
                label = vol.get("FileSystemLabel") or None
                fstype = vol.get("FileSystem")

        result.append({
            "name": drive_letter or f"Part{part.get('PartitionNumber', '?')}",
            "device": drive_letter or f"Disk{disk_num}p{part.get('PartitionNumber', 0)}",
            "size": f"{part.get('Size', 0) / 1024**3:.1f}G",
            "mountpoint": mountpoint,
            "fstype": fstype,
            "label": label,
        })

    return result


def format_sd_card(device: str, label: str = "SDCARD",
                   cluster_sectors_fn=None) -> tuple[bool, str]:
    """Format a removable drive as FAT32 on Windows using diskpart."""
    disk_num = _disk_number_from_device(device)
    if disk_num is None:
        return False, f"Cannot determine disk number from: {device}"

    label = (label or "SDCARD")[:11].upper()
    if not _SAFE_LABEL_RE.match(label):
        return False, f"Invalid volume label: {label!r}"

    # Build diskpart script
    # Allocation unit size: cluster_sectors * 512 bytes
    alloc_size = 32768  # Default 32K
    if cluster_sectors_fn:
        # Get disk size for the callback
        size_data = _ps_json(f"(Get-Disk -Number {disk_num}).Size")
        size_bytes = int(size_data) if size_data else 0
        sectors = cluster_sectors_fn(size_bytes)
        alloc_size = int(sectors) * 512

    diskpart_script = f"""select disk {disk_num}
clean
create partition primary
select partition 1
active
format fs=fat32 label="{label}" quick allocation={alloc_size}
assign
"""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, dir=tempfile.gettempdir()
    ) as f:
        f.write(diskpart_script)
        script_path = f.name

    try:
        res = _elevate_and_run(
            f'diskpart /s "{script_path}"',
            timeout=300,
        )
        if res.returncode != 0 or "error" in res.stderr.lower():
            error = res.stderr.strip() or res.stdout.strip()
            return False, f"Format failed: {error}"
    finally:
        try:
            os.unlink(script_path)
        except OSError:
            pass

    return True, f"Successfully formatted Disk {disk_num} as FAT32 (label={label})"


def check_disk(partition: str) -> str:
    """Run chkdsk on a partition (drive letter like 'E:')."""
    # Extract drive letter
    drive = partition.rstrip("\\")
    if not re.match(r"^[A-Z]:?$", drive, re.IGNORECASE):
        return f"Invalid partition for Windows check: {partition}"

    if not drive.endswith(":"):
        drive += ":"

    res = _elevate_and_run(f'chkdsk {drive}', timeout=300)
    output = (res.stdout + "\n" + res.stderr).strip()
    return output


def eject_drive(device: str) -> tuple[bool, str]:
    """Eject a removable drive on Windows."""
    disk_num = _disk_number_from_device(device)
    if disk_num is None:
        return False, f"Cannot determine disk number from: {device}"

    # Get drive letters to eject
    parts = get_drive_partitions(device)
    for part in parts:
        dl = part.get("name", "").rstrip(":")
        if dl and len(dl) == 1:
            _ps(f"$vol = Get-WmiObject -Class Win32_Volume -Filter \"DriveLetter='{dl}:'\"; "
                f"if ($vol) {{ $vol.Dismount($false, $false) }}")

    # Set disk offline
    res = _ps(f"Set-Disk -Number {disk_num} -IsOffline $true -ErrorAction SilentlyContinue")
    if res.returncode == 0:
        return True, f"Disk {disk_num} has been safely ejected."

    return True, f"Disk {disk_num} volumes dismounted. You may safely remove the card."


def mount_partition(partition: str) -> str | None:
    """Ensure a partition is mounted and return its drive letter path."""
    # If it's already a drive letter path, just verify it exists
    if re.match(r"^[A-Z]:", partition, re.IGNORECASE):
        path = partition.rstrip("\\") + "\\"
        if os.path.isdir(path):
            return path
        return None

    # If it's a disk number reference, find the drive letter
    disk_num = _disk_number_from_device(partition)
    if disk_num is not None:
        parts = get_drive_partitions(str(disk_num))
        for p in parts:
            if p.get("mountpoint"):
                return p["mountpoint"]

        # Try to assign a drive letter
        _ps(f"Get-Partition -DiskNumber {disk_num} | "
            f"Where-Object {{ -not $_.DriveLetter }} | "
            f"Add-PartitionAccessPath -AssignDriveLetter -ErrorAction SilentlyContinue")

        # Re-check
        parts = get_drive_partitions(str(disk_num))
        for p in parts:
            if p.get("mountpoint"):
                return p["mountpoint"]

    return None


def unmount_partition(partition: str) -> tuple[bool, str]:
    """Unmount (dismount) a partition on Windows."""
    drive = partition.rstrip("\\")
    if not re.match(r"^[A-Z]:?$", drive, re.IGNORECASE):
        return False, f"Invalid partition: {partition}"
    if not drive.endswith(":"):
        drive += ":"

    dl = drive[0]
    res = _ps(
        f"$vol = Get-WmiObject -Class Win32_Volume -Filter \"DriveLetter='{dl}:'\"; "
        f"if ($vol) {{ $vol.Dismount($false, $false) }}"
    )
    if res.returncode == 0:
        return True, f"Unmounted {drive}."
    return False, f"Failed to unmount {drive}: {res.stderr.strip()}"


def unmount_all_partitions(device: str) -> tuple[bool, str]:
    """Unmount all partitions on a disk."""
    parts = get_drive_partitions(device)
    failed = []
    for part in parts:
        if part.get("mountpoint"):
            ok, msg = unmount_partition(part["device"])
            if not ok:
                failed.append(part["device"])
    if failed:
        return False, f"Failed to unmount: {', '.join(failed)}"
    return True, "All partitions unmounted."


def write_image_to_device(
    img_path: str,
    device: str,
    timeout: int = 3600,
) -> tuple[bool, str]:
    """Write a raw .img file to a physical drive on Windows.

    Uses direct file I/O to \\\\.\\PhysicalDriveN with admin privileges.
    """
    disk_num = _disk_number_from_device(device)
    if disk_num is None:
        return False, f"Cannot determine disk number from: {device}"

    if not os.path.isfile(img_path):
        return False, f"Image file not found: {img_path}"

    img_size = os.path.getsize(img_path)
    physical_drive = f"\\\\.\\PhysicalDrive{disk_num}"

    # Unmount all volumes first
    unmount_all_partitions(device)

    # Set disk offline to release all handles, then write
    # Use a PowerShell script that handles the raw write with admin privileges
    ps_script = f"""
Set-Disk -Number {disk_num} -IsOffline $true -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1

$source = [System.IO.File]::OpenRead('{img_path.replace("'", "''")}')
$dest = [System.IO.File]::Open('{physical_drive}', [System.IO.FileMode]::Open, [System.IO.FileAccess]::Write, [System.IO.FileShare]::None)

$buffer = New-Object byte[] 4194304  # 4MB buffer
$totalWritten = 0
$sourceLength = $source.Length

while ($true) {{
    $bytesRead = $source.Read($buffer, 0, $buffer.Length)
    if ($bytesRead -eq 0) {{ break }}
    $dest.Write($buffer, 0, $bytesRead)
    $totalWritten += $bytesRead
}}

$dest.Flush()
$dest.Close()
$source.Close()

Set-Disk -Number {disk_num} -IsOffline $false -ErrorAction SilentlyContinue
Write-Output "Successfully wrote $totalWritten bytes to PhysicalDrive{disk_num}"
"""

    res = _elevate_and_run(ps_script, timeout=timeout)
    if res.returncode != 0 or "error" in res.stderr.lower():
        error = res.stderr.strip() or res.stdout.strip()
        return False, f"Image write failed: {error}"

    return True, f"Image written successfully to PhysicalDrive{disk_num}."
