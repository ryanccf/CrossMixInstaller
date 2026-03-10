#!/usr/bin/env python3
"""
CrossMix Installer - Linux Desktop Tools for CrossMix OS
Manages CrossMix OS installation on TrimUI Smart Pro SD cards.
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib, Pango

import os
import sys
import threading
import shutil
import subprocess
from pathlib import Path

from lib.sd_manager import (
    list_removable_drives, detect_sd_state, get_crossmix_version,
    format_sd_card, check_disk, eject_drive, mount_partition,
    unmount_partition, get_free_space, get_drive_partitions
)
from lib.crossmix_installer import (
    fetch_releases, download_release, extract_to_sd,
    verify_extraction, get_required_space, get_downloaded_releases
)
from lib.bios_manager import (
    BIOS_FILES, download_all_bios, install_bios_to_sd,
    scan_sd_bios, scan_cached_bios,
)

APP_NAME = "CrossMix Installer"
APP_VERSION = "0.1.0"
APP_DIR = Path(__file__).parent.resolve()
DOWNLOADS_DIR = APP_DIR / "downloads"
BIOS_CACHE_DIR = APP_DIR / "bios_cache"

DOWNLOADS_DIR.mkdir(exist_ok=True)
BIOS_CACHE_DIR.mkdir(exist_ok=True)


class DriveSelector(Gtk.Dialog):
    """Dialog to select a removable drive."""

    def __init__(self, parent):
        super().__init__(
            title="Select SD Card",
            transient_for=parent,
            modal=True,
            destroy_with_parent=True,
        )
        self.set_default_size(450, 300)
        self.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OK, Gtk.ResponseType.OK,
        )
        self.selected_drive = None

        content = self.get_content_area()
        content.set_spacing(10)
        content.set_margin_start(15)
        content.set_margin_end(15)
        content.set_margin_top(15)
        content.set_margin_bottom(15)

        label = Gtk.Label(label="Select the SD card to use:")
        label.set_halign(Gtk.Align.START)
        content.pack_start(label, False, False, 0)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_min_content_height(200)
        content.pack_start(scrolled, True, True, 0)

        self.radio_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        scrolled.add(self.radio_box)

        self._populate_drives()
        self.show_all()

    def _populate_drives(self):
        drives = list_removable_drives()
        if not drives:
            label = Gtk.Label(label="No removable drives detected.\nInsert an SD card and try again.")
            label.set_halign(Gtk.Align.START)
            self.radio_box.pack_start(label, False, False, 0)
            return

        first_radio = None
        for drive in drives:
            text = f"/dev/{drive['name']} - {drive['size']} - {drive.get('model', 'Unknown')}"
            if drive.get('label'):
                text += f" [{drive['label']}]"

            if first_radio is None:
                radio = Gtk.RadioButton.new_with_label(None, text)
                first_radio = radio
            else:
                radio = Gtk.RadioButton.new_with_label_from_widget(first_radio, text)

            radio.drive_info = drive
            radio.connect("toggled", self._on_radio_toggled)
            self.radio_box.pack_start(radio, False, False, 0)

        if first_radio:
            first_radio.set_active(True)
            self.selected_drive = first_radio.drive_info

    def _on_radio_toggled(self, button):
        if button.get_active():
            self.selected_drive = button.drive_info


class ProgressDialog(Gtk.Dialog):
    """Progress dialog with a progress bar and status label."""

    def __init__(self, parent, title="Working..."):
        super().__init__(
            title=title,
            transient_for=parent,
            modal=True,
            destroy_with_parent=True,
        )
        self.set_default_size(400, 120)
        self.set_deletable(False)

        content = self.get_content_area()
        content.set_spacing(10)
        content.set_margin_start(20)
        content.set_margin_end(20)
        content.set_margin_top(20)
        content.set_margin_bottom(20)

        self.status_label = Gtk.Label(label="Starting...")
        self.status_label.set_halign(Gtk.Align.START)
        self.status_label.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        content.pack_start(self.status_label, False, False, 0)

        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_show_text(True)
        content.pack_start(self.progress_bar, False, False, 0)

        self.show_all()

    def set_progress(self, fraction, text=None):
        GLib.idle_add(self._update_progress, fraction, text)

    def _update_progress(self, fraction, text):
        self.progress_bar.set_fraction(min(fraction, 1.0))
        if text:
            self.status_label.set_text(text)
        return False


class CrossMixInstaller(Gtk.Window):
    """Main application window."""

    def __init__(self):
        super().__init__(title=f"{APP_NAME} v{APP_VERSION}")
        self.set_default_size(520, 380)
        self.set_resizable(False)
        self.set_position(Gtk.WindowPosition.CENTER)

        self.connect("destroy", Gtk.main_quit)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(main_box)

        self.notebook = Gtk.Notebook()
        self.notebook.set_margin_start(5)
        self.notebook.set_margin_end(5)
        self.notebook.set_margin_top(5)
        main_box.pack_start(self.notebook, True, True, 0)

        self._build_install_tab()
        self._build_bios_tab()
        self._build_sdtools_tab()
        self._build_about_tab()

        # Bottom bar
        bottom_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        bottom_bar.set_margin_start(10)
        bottom_bar.set_margin_end(10)
        bottom_bar.set_margin_top(5)
        bottom_bar.set_margin_bottom(10)
        main_box.pack_end(bottom_bar, False, False, 0)

        self.ok_button = Gtk.Button(label="OK")
        self.ok_button.set_size_request(90, 32)
        self.ok_button.connect("clicked", self._on_ok_clicked)
        bottom_bar.pack_end(self.ok_button, False, False, 0)

        eject_button = Gtk.Button(label="Eject SD")
        eject_button.set_size_request(90, 32)
        eject_button.connect("clicked", self._on_eject_clicked)
        bottom_bar.pack_end(eject_button, False, False, 0)

        self.notebook.connect("switch-page", self._on_tab_changed)

    # -- Tab 1: Install or Update CrossMix --

    def _build_install_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        box.set_margin_start(15)
        box.set_margin_end(15)
        box.set_margin_top(15)
        box.set_margin_bottom(15)

        frame = Gtk.Frame(label="Install or Update CrossMix OS")
        frame.set_margin_bottom(10)
        box.pack_start(frame, True, True, 0)

        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        inner.set_margin_start(20)
        inner.set_margin_end(20)
        inner.set_margin_top(15)
        inner.set_margin_bottom(15)
        frame.add(inner)

        desc = Gtk.Label(
            label="Install CrossMix OS on an SD card for TrimUI Smart Pro.\n"
                  "Download the latest release from GitHub and extract to SD."
        )
        desc.set_halign(Gtk.Align.START)
        desc.set_line_wrap(True)
        inner.pack_start(desc, False, False, 0)

        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        inner.pack_start(sep, False, False, 5)

        self.install_radios = []

        r1 = Gtk.RadioButton.new_with_label(None, "Install / Upgrade / Reinstall CrossMix (without formatting)")
        r1.action = "install_no_format"
        self.install_radios.append(r1)
        inner.pack_start(r1, False, False, 0)

        r2 = Gtk.RadioButton.new_with_label_from_widget(r1, "Format SD card and install CrossMix")
        r2.action = "format_and_install"
        self.install_radios.append(r2)
        inner.pack_start(r2, False, False, 0)

        self.notebook.append_page(box, Gtk.Label(label="Install / Update"))

    # -- Tab 2: BIOS Manager --

    def _build_bios_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        box.set_margin_start(15)
        box.set_margin_end(15)
        box.set_margin_top(15)
        box.set_margin_bottom(15)

        frame = Gtk.Frame(label="BIOS Manager")
        frame.set_margin_bottom(10)
        box.pack_start(frame, True, True, 0)

        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        inner.set_margin_start(20)
        inner.set_margin_end(20)
        inner.set_margin_top(15)
        inner.set_margin_bottom(15)
        frame.add(inner)

        desc = Gtk.Label(
            label="Download and install BIOS files required by emulators.\n"
                  "Files are cached locally and can be installed to any SD card."
        )
        desc.set_halign(Gtk.Align.START)
        desc.set_line_wrap(True)
        inner.pack_start(desc, False, False, 0)

        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        inner.pack_start(sep, False, False, 5)

        self.bios_status_label = Gtk.Label(label="Scanning...")
        self.bios_status_label.set_halign(Gtk.Align.START)
        inner.pack_start(self.bios_status_label, False, False, 0)

        self.bios_required_only = Gtk.CheckButton(label="Required BIOS files only")
        self.bios_required_only.set_active(False)
        inner.pack_start(self.bios_required_only, False, False, 0)

        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        btn_box.set_margin_top(10)
        inner.pack_start(btn_box, False, False, 0)

        dl_btn = Gtk.Button(label="Download All to Cache")
        dl_btn.connect("clicked", self._on_bios_download)
        btn_box.pack_start(dl_btn, False, False, 0)

        inst_btn = Gtk.Button(label="Install to SD Card")
        inst_btn.connect("clicked", self._on_bios_install)
        btn_box.pack_start(inst_btn, False, False, 0)

        self.notebook.append_page(box, Gtk.Label(label="BIOS Manager"))
        GLib.idle_add(self._update_bios_status)

    def _update_bios_status(self):
        cached = scan_cached_bios(BIOS_CACHE_DIR)
        total_files = len(BIOS_FILES)
        cached_count = sum(1 for v in cached.values() if v)
        required_files = [e for e in BIOS_FILES if e["required"]]
        required_total = len(required_files)
        required_cached = sum(1 for e in required_files if cached.get(e["filename"], False))
        self.bios_status_label.set_text(
            f"Cached: {cached_count}/{total_files} files "
            f"({required_cached}/{required_total} required)"
        )
        return False

    def _on_bios_download(self, button):
        required_only = self.bios_required_only.get_active()
        progress = ProgressDialog(self, "Downloading BIOS Files")

        def worker():
            try:
                def cb(fraction, text):
                    GLib.idle_add(progress.set_progress, fraction, text)

                ok, succeeded, failed = download_all_bios(
                    BIOS_CACHE_DIR, progress_cb=cb,
                    skip_cached=True, required_only=required_only,
                )

                GLib.idle_add(progress.set_progress, 1.0, "Done!")
                GLib.idle_add(self._update_bios_status)

                if ok:
                    GLib.idle_add(
                        self._show_success_and_close_progress, progress,
                        f"Downloaded {len(succeeded)} BIOS files successfully."
                    )
                else:
                    summary = f"Downloaded {len(succeeded)} files.\n\nFailed ({len(failed)}):\n"
                    summary += "\n".join(failed[:10])
                    GLib.idle_add(
                        self._show_error_and_close_progress, progress, summary
                    )
            except Exception as e:
                GLib.idle_add(self._show_error_and_close_progress, progress, str(e))

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    def _on_bios_install(self, button):
        cached = scan_cached_bios(BIOS_CACHE_DIR)
        if not any(cached.values()):
            self._show_message(
                "No BIOS Files",
                "No BIOS files found in cache.\nDownload them first using 'Download All to Cache'.",
                Gtk.MessageType.WARNING,
            )
            return

        device, mount_point = self._select_drive()
        if not device:
            return
        if not mount_point:
            self._show_message("Error", "Could not mount SD card.", Gtk.MessageType.ERROR)
            return

        required_only = self.bios_required_only.get_active()
        progress = ProgressDialog(self, "Installing BIOS Files")

        def worker():
            try:
                def cb(fraction, text):
                    GLib.idle_add(progress.set_progress, fraction, text)

                ok, succeeded, failed = install_bios_to_sd(
                    BIOS_CACHE_DIR, Path(mount_point),
                    progress_cb=cb, required_only=required_only,
                )

                GLib.idle_add(progress.set_progress, 1.0, "Done!")

                if ok:
                    GLib.idle_add(
                        self._show_success_and_close_progress, progress,
                        f"Installed {len(succeeded)} BIOS files to SD card."
                    )
                else:
                    summary = f"Installed {len(succeeded)} files.\n\nFailed ({len(failed)}):\n"
                    summary += "\n".join(failed[:10])
                    GLib.idle_add(
                        self._show_error_and_close_progress, progress, summary
                    )
            except Exception as e:
                GLib.idle_add(self._show_error_and_close_progress, progress, str(e))

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    # -- Tab 3: SD Card Tools --

    def _build_sdtools_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        box.set_margin_start(15)
        box.set_margin_end(15)
        box.set_margin_top(15)
        box.set_margin_bottom(15)

        frame = Gtk.Frame(label="SD Card Tools")
        frame.set_margin_bottom(10)
        box.pack_start(frame, True, True, 0)

        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        inner.set_margin_start(20)
        inner.set_margin_end(20)
        inner.set_margin_top(15)
        inner.set_margin_bottom(15)
        frame.add(inner)

        self.sdtools_radios = []

        r1 = Gtk.RadioButton.new_with_label(None, "Format SD card in FAT32 (label: CROSSMIX)")
        r1.action = "format_fat32"
        self.sdtools_radios.append(r1)
        inner.pack_start(r1, False, False, 0)

        r2 = Gtk.RadioButton.new_with_label_from_widget(r1, "Check for errors (fsck)")
        r2.action = "check_disk"
        self.sdtools_radios.append(r2)
        inner.pack_start(r2, False, False, 0)

        self.notebook.append_page(box, Gtk.Label(label="SD Card Tools"))

    # -- Tab 4: About --

    def _build_about_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_margin_start(15)
        box.set_margin_end(15)
        box.set_margin_top(15)
        box.set_margin_bottom(15)

        title = Gtk.Label()
        title.set_markup(f"<b>{APP_NAME}</b> v{APP_VERSION}")
        title.set_halign(Gtk.Align.START)
        box.pack_start(title, False, False, 0)

        desc = Gtk.Label(
            label="Install and manage CrossMix OS on TrimUI Smart Pro SD cards.\n"
                  "CrossMix OS by cizia64."
        )
        desc.set_halign(Gtk.Align.START)
        desc.set_line_wrap(True)
        box.pack_start(desc, False, False, 0)

        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        box.pack_start(sep, False, False, 5)

        links_label = Gtk.Label()
        links_label.set_markup(
            '<a href="https://github.com/cizia64/CrossMix-OS">CrossMix OS on GitHub</a>\n'
            '<a href="https://github.com/cizia64/CrossMix-OS/wiki">CrossMix OS Wiki</a>'
        )
        links_label.set_halign(Gtk.Align.START)
        links_label.set_line_wrap(True)
        box.pack_start(links_label, False, False, 0)

        self.notebook.append_page(box, Gtk.Label(label="About"))

    # -- Event Handlers --

    def _on_tab_changed(self, notebook, page, page_num):
        # Hide OK button on BIOS tab (has its own buttons) and About tab
        self.ok_button.set_visible(page_num not in (1, 3))

    def _on_ok_clicked(self, button):
        page = self.notebook.get_current_page()
        if page == 0:
            self._handle_install_action()
        elif page == 2:
            self._handle_sdtools_action()

    def _on_eject_clicked(self, button):
        dialog = DriveSelector(self)
        response = dialog.run()
        drive = dialog.selected_drive
        dialog.destroy()

        if response != Gtk.ResponseType.OK or not drive:
            return

        device = f"/dev/{drive['name']}"
        success, msg = eject_drive(device)
        self._show_message(
            "Eject SD Card",
            msg,
            Gtk.MessageType.INFO if success else Gtk.MessageType.ERROR
        )

    # -- Install Actions --

    def _get_selected_radio(self, radios):
        for r in radios:
            if r.get_active():
                return r.action
        return None

    def _select_drive(self):
        """Show drive selector and return (device, mount_point) or (None, None)."""
        dialog = DriveSelector(self)
        response = dialog.run()
        drive = dialog.selected_drive
        dialog.destroy()

        if response != Gtk.ResponseType.OK or not drive:
            return None, None

        device = f"/dev/{drive['name']}"
        partitions = get_drive_partitions(drive['name'])
        if partitions:
            part_dev = f"/dev/{partitions[0]['name']}"
            mount_point = partitions[0].get('mountpoint')
            if not mount_point:
                mount_point = mount_partition(part_dev)
            return device, mount_point
        return device, None

    def _handle_install_action(self):
        action = self._get_selected_radio(self.install_radios)
        if action == "install_no_format":
            self._do_install(format_first=False)
        elif action == "format_and_install":
            self._do_install(format_first=True)

    def _do_install(self, format_first=False):
        device, mount_point = self._select_drive()
        if not device:
            return

        if format_first:
            confirm = self._confirm(
                "Format SD Card",
                f"This will ERASE ALL DATA on {device}.\nAre you sure you want to format and install CrossMix?"
            )
            if not confirm:
                return

        # Show release picker
        release_dialog = ReleasePicker(self)
        response = release_dialog.run()
        release = release_dialog.selected_release
        release_dialog.destroy()

        if response != Gtk.ResponseType.OK or not release:
            return

        def worker():
            try:
                if format_first:
                    GLib.idle_add(progress.set_progress, 0.05, "Formatting SD card...")
                    success, msg = format_sd_card(device)
                    if not success:
                        GLib.idle_add(self._show_error_and_close_progress, progress, f"Format failed: {msg}")
                        return
                    import time
                    GLib.idle_add(progress.set_progress, 0.08, "Waiting for drive to settle...")
                    time.sleep(3)
                    nonlocal mount_point
                    mount_point = None
                    dev_name = device.replace('/dev/', '')
                    for attempt in range(5):
                        partitions = get_drive_partitions(dev_name)
                        if partitions:
                            part_dev = f"/dev/{partitions[0]['name']}"
                            mount_point = mount_partition(part_dev)
                            if mount_point:
                                break
                        time.sleep(2)

                if not mount_point:
                    GLib.idle_add(self._show_error_and_close_progress, progress, "Could not mount SD card.")
                    return

                # Download if needed
                zip_path = None
                if release.get('local_path'):
                    zip_path = release['local_path']
                else:
                    GLib.idle_add(progress.set_progress, 0.1, "Downloading CrossMix OS...")
                    def dl_progress(downloaded, total):
                        if total > 0:
                            frac = 0.1 + 0.5 * (downloaded / total)
                            size_mb = downloaded / (1024 * 1024)
                            total_mb = total / (1024 * 1024)
                            GLib.idle_add(progress.set_progress, frac, f"Downloading: {size_mb:.1f} / {total_mb:.1f} MB")
                    zip_path = download_release(release['url'], str(DOWNLOADS_DIR), dl_progress)

                # Extract
                GLib.idle_add(progress.set_progress, 0.6, "Extracting CrossMix OS to SD card...")
                def ext_progress(current_file, idx, total):
                    frac = 0.6 + 0.35 * (idx / max(total, 1))
                    GLib.idle_add(progress.set_progress, frac, f"Extracting: {current_file}")

                success, msg = extract_to_sd(zip_path, mount_point, ext_progress)
                if not success:
                    GLib.idle_add(self._show_error_and_close_progress, progress, f"Extract failed: {msg}")
                    return

                # Verify
                GLib.idle_add(progress.set_progress, 0.97, "Verifying installation...")
                success, missing = verify_extraction(mount_point)

                GLib.idle_add(progress.set_progress, 1.0, "Done!")
                if success:
                    GLib.idle_add(self._show_success_and_close_progress, progress,
                                  "CrossMix OS installed successfully!\n\n"
                                  "You can now eject the SD card and insert it into your TrimUI Smart Pro.\n"
                                  "The first boot may take a bit longer as CrossMix sets up.")
                else:
                    GLib.idle_add(self._show_error_and_close_progress, progress,
                                  f"Installation completed but some directories are missing:\n{', '.join(missing)}")

            except Exception as e:
                GLib.idle_add(self._show_error_and_close_progress, progress, str(e))

        progress = ProgressDialog(self, "Installing CrossMix OS")
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    # -- SD Card Tools Actions --

    def _handle_sdtools_action(self):
        action = self._get_selected_radio(self.sdtools_radios)
        if action == "format_fat32":
            self._do_format()
        elif action == "check_disk":
            self._do_check_disk()

    def _do_format(self):
        dialog = DriveSelector(self)
        response = dialog.run()
        drive = dialog.selected_drive
        dialog.destroy()

        if response != Gtk.ResponseType.OK or not drive:
            return

        device = f"/dev/{drive['name']}"
        confirm = self._confirm(
            "Format SD Card",
            f"This will ERASE ALL DATA on {device} ({drive['size']}).\n\nAre you sure?"
        )
        if not confirm:
            return

        progress = ProgressDialog(self, "Formatting SD Card")

        def worker():
            GLib.idle_add(progress.set_progress, 0.2, f"Formatting {device}...")
            success, msg = format_sd_card(device)
            GLib.idle_add(progress.set_progress, 1.0, "Done!")
            if success:
                GLib.idle_add(self._show_success_and_close_progress, progress, msg)
            else:
                GLib.idle_add(self._show_error_and_close_progress, progress, msg)

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    def _do_check_disk(self):
        dialog = DriveSelector(self)
        response = dialog.run()
        drive = dialog.selected_drive
        dialog.destroy()

        if response != Gtk.ResponseType.OK or not drive:
            return

        device = f"/dev/{drive['name']}"
        partitions = get_drive_partitions(drive['name'])
        if not partitions:
            self._show_message("Error", "No partitions found on this drive.", Gtk.MessageType.ERROR)
            return

        part_dev = f"/dev/{partitions[0]['name']}"
        result = check_disk(part_dev)
        self._show_message("Disk Check Results", result, Gtk.MessageType.INFO)

    # -- Helper Methods --

    def _show_message(self, title, message, msg_type=Gtk.MessageType.INFO):
        dialog = Gtk.MessageDialog(
            transient_for=self,
            modal=True,
            message_type=msg_type,
            buttons=Gtk.ButtonsType.OK,
            text=title,
        )
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()

    def _confirm(self, title, message):
        dialog = Gtk.MessageDialog(
            transient_for=self,
            modal=True,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.YES_NO,
            text=title,
        )
        dialog.format_secondary_text(message)
        response = dialog.run()
        dialog.destroy()
        return response == Gtk.ResponseType.YES

    def _show_error_and_close_progress(self, progress, message):
        progress.destroy()
        self._show_message("Error", message, Gtk.MessageType.ERROR)
        return False

    def _show_success_and_close_progress(self, progress, message):
        progress.destroy()
        self._show_message("Success", message, Gtk.MessageType.INFO)
        return False


class ReleasePicker(Gtk.Dialog):
    """Dialog to pick a CrossMix OS release to download/use."""

    def __init__(self, parent):
        super().__init__(
            title="Select CrossMix OS Release",
            transient_for=parent,
            modal=True,
        )
        self.set_default_size(500, 400)
        self.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OK, Gtk.ResponseType.OK,
        )
        self.selected_release = None

        content = self.get_content_area()
        content.set_spacing(10)
        content.set_margin_start(15)
        content.set_margin_end(15)
        content.set_margin_top(15)
        content.set_margin_bottom(15)

        # Already downloaded section
        downloaded = get_downloaded_releases(str(DOWNLOADS_DIR))
        if downloaded:
            local_frame = Gtk.Frame(label="Already Downloaded")
            local_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
            local_box.set_margin_start(10)
            local_box.set_margin_end(10)
            local_box.set_margin_top(10)
            local_box.set_margin_bottom(10)
            local_frame.add(local_box)
            content.pack_start(local_frame, False, False, 0)

            self.first_radio = None
            for dl in downloaded:
                size_mb = dl['size'] / (1024 * 1024)
                text = f"{dl['filename']} ({size_mb:.1f} MB)"
                if self.first_radio is None:
                    radio = Gtk.RadioButton.new_with_label(None, text)
                    self.first_radio = radio
                else:
                    radio = Gtk.RadioButton.new_with_label_from_widget(self.first_radio, text)
                radio.release_info = {'local_path': dl['path'], 'name': dl['filename']}
                radio.connect("toggled", self._on_release_toggled)
                local_box.pack_start(radio, False, False, 0)
        else:
            self.first_radio = None

        # Online releases section
        online_frame = Gtk.Frame(label="Download from GitHub")
        online_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        online_box.set_margin_start(10)
        online_box.set_margin_end(10)
        online_box.set_margin_top(10)
        online_box.set_margin_bottom(10)
        online_frame.add(online_box)
        content.pack_start(online_frame, True, True, 0)

        loading_label = Gtk.Label(label="Fetching releases from GitHub...")
        online_box.pack_start(loading_label, False, False, 0)

        self.online_box = online_box
        self.loading_label = loading_label

        thread = threading.Thread(target=self._fetch_releases, daemon=True)
        thread.start()

        self.show_all()

    def _fetch_releases(self):
        try:
            release_data = fetch_releases()
            releases = release_data.get('stable', []) + release_data.get('beta', [])
            GLib.idle_add(self._populate_releases, releases)
        except Exception as e:
            GLib.idle_add(self._show_fetch_error, str(e))

    def _populate_releases(self, releases):
        self.loading_label.destroy()
        if not releases:
            label = Gtk.Label(label="No releases found.")
            self.online_box.pack_start(label, False, False, 0)
            label.show()
            return

        for rel in releases[:10]:
            size_mb = rel.get('size', 0) / (1024 * 1024)
            pre = " [BETA]" if rel.get('prerelease') else ""
            text = f"{rel['name']}{pre} ({size_mb:.1f} MB)"

            if self.first_radio is None:
                radio = Gtk.RadioButton.new_with_label(None, text)
                self.first_radio = radio
            else:
                radio = Gtk.RadioButton.new_with_label_from_widget(self.first_radio, text)

            radio.release_info = {'url': rel['browser_download_url'], 'name': rel['name']}
            radio.connect("toggled", self._on_release_toggled)
            self.online_box.pack_start(radio, False, False, 0)
            radio.show()

        if self.first_radio:
            self.first_radio.set_active(True)
            self.selected_release = self.first_radio.release_info

    def _show_fetch_error(self, error):
        self.loading_label.set_text(f"Failed to fetch releases: {error}")

    def _on_release_toggled(self, button):
        if button.get_active():
            self.selected_release = button.release_info


def check_dependencies():
    """Check for required system tools and offer to install missing ones."""
    REQUIRED_TOOLS = {
        "parted":    "parted",
        "mkfs.vfat": "dosfstools",
        "fsck.vfat": "dosfstools",
        "partprobe": "parted",
        "udisksctl": "udisks2",
        "eject":     "eject",
        "udevadm":   "udev",
        "lsblk":     "util-linux",
    }

    missing_pkgs = set()
    for cmd, pkg in REQUIRED_TOOLS.items():
        if not (shutil.which(cmd)
                or os.path.isfile(f"/sbin/{cmd}")
                or os.path.isfile(f"/usr/sbin/{cmd}")):
            missing_pkgs.add(pkg)

    if not missing_pkgs:
        return True

    pkg_list = " ".join(sorted(missing_pkgs))
    print(f"Missing packages: {pkg_list}")
    print("Attempting to install...")

    result = subprocess.run(
        ["pkexec", "apt-get", "install", "-y"] + sorted(missing_pkgs),
        capture_output=False,
    )
    return result.returncode == 0


def main():
    if not check_dependencies():
        print("Some dependencies could not be installed. The app may not work correctly.")

    css = b"""
    window {
        font-size: 10pt;
    }
    """
    style_provider = Gtk.CssProvider()
    style_provider.load_from_data(css)
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(),
        style_provider,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
    )

    win = CrossMixInstaller()
    win.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
