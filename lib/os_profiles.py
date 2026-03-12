"""
os_profiles.py - OS profile definitions for supported operating systems.

Each profile contains all the OS-specific configuration: GitHub repo,
expected directories, SD card label, BIOS file lists, and detection logic.
"""

# ---------------------------------------------------------------------------
# BIOS repo path mappings (shared source repo)
# ---------------------------------------------------------------------------

SYSTEM_TO_REPO_PATH = {
    "PlayStation": "Sony - PlayStation/",
    "Neo Geo": "Arcade/",
    "Neo Geo CD": "SNK - NeoGeo CD/",
    "Sega CD": "Sega - Mega CD - Sega CD/",
    "TurboGrafx-CD": "NEC - PC Engine - TurboGrafx 16 - SuperGrafx/",
    "Saturn": "Sega - Saturn/",
    "Dreamcast": "Sega - Dreamcast/",
    "GBA": "Nintendo - Game Boy Advance/",
    "GB": "Nintendo - Gameboy/",
    "GBC": "Nintendo - Gameboy Color/",
    "3DO": "3DO Company, The - 3DO/",
    "Atari 5200": "Atari - 5200/",
    "Atari 7800": "Atari - 7800/",
    "Atari 800": "Atari - 400-800/",
    "ColecoVision": "Coleco - ColecoVision/",
    "Channel F": "Fairchild Channel F/",
    "Intellivision": "Mattel - Intellivision/",
    "PC-FX": "NEC - PC-FX/",
    "Odyssey 2": "Magnavox - Odyssey2/",
    "FDS": "Nintendo - Family Computer Disk System/",
    "Atari Lynx": "Atari - Lynx/",
    "Pokemon Mini": "Nintendo - Pokemon Mini/",
}

# ---------------------------------------------------------------------------
# BIOS file lists
# ---------------------------------------------------------------------------

ONION_BIOS_FILES = [
    # --- PlayStation (required) ---
    {"filename": "scph1001.bin", "system": "PlayStation", "md5": "924e392ed05558ffdb115408c263dccf", "required": True, "subdir": "", "extra_copies": [], "notes": "PS1 BIOS (North America)"},
    {"filename": "scph5500.bin", "system": "PlayStation", "md5": "8dd7d5296a650fac7319bce665a6a53c", "required": True, "subdir": "", "extra_copies": [], "notes": "PS1 BIOS (Japan)"},
    {"filename": "scph5501.bin", "system": "PlayStation", "md5": "490f666e1afb15b7362b406ed1cea246", "required": True, "subdir": "", "extra_copies": [], "notes": "PS1 BIOS (North America)"},
    {"filename": "scph5502.bin", "system": "PlayStation", "md5": "32736f17079d0b2b7024407c39bd3050", "required": True, "subdir": "", "extra_copies": [], "notes": "PS1 BIOS (Europe)"},
    # --- Neo Geo (required) ---
    {"filename": "neogeo.zip", "system": "Neo Geo", "md5": "", "required": True, "subdir": "", "extra_copies": ["Roms/NEOGEO/neogeo.zip"], "notes": "Neo Geo BIOS (also needed in Roms/NEOGEO/)"},
    # --- Sega CD (required) ---
    {"filename": "bios_CD_U.bin", "system": "Sega CD", "md5": "2efd74e3232ff260e371b99f84024f7f", "required": True, "subdir": "", "extra_copies": [], "notes": "Sega CD BIOS (North America)"},
    {"filename": "bios_CD_E.bin", "system": "Sega CD", "md5": "e66fa1dc5820d254611fdcdba0662372", "required": True, "subdir": "", "extra_copies": [], "notes": "Sega CD BIOS (Europe)"},
    {"filename": "bios_CD_J.bin", "system": "Sega CD", "md5": "278a9397d192149e84e820ac621a8edd", "required": True, "subdir": "", "extra_copies": [], "notes": "Sega CD BIOS (Japan)"},
    # --- TurboGrafx-CD (required) ---
    {"filename": "syscard3.pce", "system": "TurboGrafx-CD", "md5": "38179df8f4ac870017db21ebcbf53114", "required": True, "subdir": "", "extra_copies": [], "notes": "TurboGrafx-CD / PC Engine CD System Card 3"},
    # --- Saturn (required) ---
    {"filename": "mpr-17933.bin", "system": "Saturn", "md5": "3240872c70984b6cbfda1586cab68dbe", "required": True, "subdir": "", "extra_copies": [], "notes": "Sega Saturn BIOS (Europe)"},
    # --- GBA (optional) ---
    {"filename": "gba_bios.bin", "system": "GBA", "md5": "a860e8c0b6d573d191e4ec7db1b1e4f6", "required": False, "subdir": "", "extra_copies": [], "notes": "Game Boy Advance BIOS (optional, HLE available)"},
    # --- GB / GBC (optional) ---
    {"filename": "gb_bios.bin", "system": "GB", "md5": "32fbbd84168d3482956eb3c5051637f5", "required": False, "subdir": "", "extra_copies": [], "notes": "Game Boy BIOS (optional)"},
    {"filename": "gbc_bios.bin", "system": "GBC", "md5": "dbfce9db9deaa2567f6a84fde55f9680", "required": False, "subdir": "", "extra_copies": [], "notes": "Game Boy Color BIOS (optional)"},
    # --- Neo Geo CD (optional) ---
    {"filename": "neocd_f.rom", "system": "Neo Geo CD", "md5": "", "required": False, "subdir": "neocd", "extra_copies": [], "notes": "Neo Geo CD front loader BIOS"},
    {"filename": "000-lo.lo", "system": "Neo Geo CD", "md5": "", "required": False, "subdir": "neocd", "extra_copies": [], "notes": "Neo Geo CD load order file"},
]

CROSSMIX_BIOS_FILES = [
    # --- PlayStation (required) ---
    {"filename": "scph5501.bin", "system": "PlayStation", "md5": "490f666e1afb15b7362b406ed1cea246", "required": True, "subdir": "", "extra_copies": [], "notes": "PS1 BIOS (North America)"},
    {"filename": "scph1001.bin", "system": "PlayStation", "md5": "924e392ed05558ffdb115408c263dccf", "required": True, "subdir": "", "extra_copies": [], "notes": "PS1 BIOS (North America, original)"},
    {"filename": "scph5500.bin", "system": "PlayStation", "md5": "8dd7d5296a650fac7319bce665a6a53c", "required": True, "subdir": "", "extra_copies": [], "notes": "PS1 BIOS (Japan)"},
    {"filename": "scph5502.bin", "system": "PlayStation", "md5": "32736f17079d0b2b7024407c39bd3050", "required": True, "subdir": "", "extra_copies": [], "notes": "PS1 BIOS (Europe)"},
    {"filename": "scph7001.bin", "system": "PlayStation", "md5": "", "required": False, "subdir": "", "extra_copies": [], "notes": "PS1 BIOS (North America, later model)"},
    {"filename": "scph101.bin", "system": "PlayStation", "md5": "", "required": False, "subdir": "", "extra_copies": [], "notes": "PS1 BIOS (PSone slim)"},
    # --- Neo Geo (required) ---
    {"filename": "neogeo.zip", "system": "Neo Geo", "md5": "", "required": True, "subdir": "", "extra_copies": [], "notes": "Neo Geo BIOS"},
    # --- Neo Geo CD (optional) ---
    {"filename": "neocd_f.rom", "system": "Neo Geo CD", "md5": "", "required": False, "subdir": "neocd", "extra_copies": [], "notes": "Neo Geo CD front loader BIOS"},
    {"filename": "000-lo.lo", "system": "Neo Geo CD", "md5": "", "required": False, "subdir": "neocd", "extra_copies": [], "notes": "Neo Geo CD load order file"},
    # --- Sega CD (required) ---
    {"filename": "bios_CD_U.bin", "system": "Sega CD", "md5": "2efd74e3232ff260e371b99f84024f7f", "required": True, "subdir": "", "extra_copies": [], "notes": "Sega CD BIOS (North America)"},
    {"filename": "bios_CD_E.bin", "system": "Sega CD", "md5": "e66fa1dc5820d254611fdcdba0662372", "required": True, "subdir": "", "extra_copies": [], "notes": "Sega CD BIOS (Europe)"},
    {"filename": "bios_CD_J.bin", "system": "Sega CD", "md5": "278a9397d192149e84e820ac621a8edd", "required": True, "subdir": "", "extra_copies": [], "notes": "Sega CD BIOS (Japan)"},
    # --- TurboGrafx-CD (required) ---
    {"filename": "syscard3.pce", "system": "TurboGrafx-CD", "md5": "38179df8f4ac870017db21ebcbf53114", "required": True, "subdir": "", "extra_copies": [], "notes": "TurboGrafx-CD / PC Engine CD System Card 3"},
    # --- Sega Saturn (required) ---
    {"filename": "mpr-17933.bin", "system": "Saturn", "md5": "3240872c70984b6cbfda1586cab68dbe", "required": True, "subdir": "", "extra_copies": [], "notes": "Sega Saturn BIOS (Europe)"},
    # --- 3DO (required) ---
    {"filename": "panafz1.bin", "system": "3DO", "md5": "", "required": True, "subdir": "", "extra_copies": [], "notes": "Panasonic 3DO FZ-1 BIOS"},
    {"filename": "panafz10.bin", "system": "3DO", "md5": "", "required": False, "subdir": "", "extra_copies": [], "notes": "Panasonic 3DO FZ-10 BIOS"},
    # --- PC-FX (optional) ---
    {"filename": "pcfx.rom", "system": "PC-FX", "md5": "", "required": False, "subdir": "", "extra_copies": [], "notes": "NEC PC-FX BIOS"},
    # --- Atari (optional) ---
    {"filename": "5200.rom", "system": "Atari 5200", "md5": "", "required": False, "subdir": "", "extra_copies": [], "notes": "Atari 5200 BIOS"},
    {"filename": "7800 BIOS (U).rom", "system": "Atari 7800", "md5": "", "required": False, "subdir": "", "extra_copies": [], "notes": "Atari 7800 BIOS (North America)"},
    {"filename": "ATARIOSA.ROM", "system": "Atari 800", "md5": "", "required": False, "subdir": "", "extra_copies": [], "notes": "Atari 800 OS-A BIOS"},
    {"filename": "ATARIOSB.ROM", "system": "Atari 800", "md5": "", "required": False, "subdir": "", "extra_copies": [], "notes": "Atari 800 OS-B BIOS"},
    {"filename": "ATARIBAS.ROM", "system": "Atari 800", "md5": "", "required": False, "subdir": "", "extra_copies": [], "notes": "Atari BASIC cartridge"},
    # --- ColecoVision (optional) ---
    {"filename": "colecovision.rom", "system": "ColecoVision", "md5": "", "required": False, "subdir": "", "extra_copies": [], "notes": "ColecoVision BIOS"},
    # --- Fairchild Channel F (optional) ---
    {"filename": "sl31253.bin", "system": "Channel F", "md5": "", "required": False, "subdir": "", "extra_copies": [], "notes": "Channel F BIOS (SL31253)"},
    {"filename": "sl31254.bin", "system": "Channel F", "md5": "", "required": False, "subdir": "", "extra_copies": [], "notes": "Channel F BIOS (SL31254)"},
    # --- Intellivision (optional) ---
    {"filename": "exec.bin", "system": "Intellivision", "md5": "", "required": False, "subdir": "", "extra_copies": [], "notes": "Intellivision Executive ROM"},
    {"filename": "grom.bin", "system": "Intellivision", "md5": "", "required": False, "subdir": "", "extra_copies": [], "notes": "Intellivision Graphics ROM"},
    # --- Odyssey 2 (optional) ---
    {"filename": "o2rom.bin", "system": "Odyssey 2", "md5": "", "required": False, "subdir": "", "extra_copies": [], "notes": "Magnavox Odyssey 2 BIOS"},
    # --- GBA (optional) ---
    {"filename": "gba_bios.bin", "system": "GBA", "md5": "a860e8c0b6d573d191e4ec7db1b1e4f6", "required": False, "subdir": "", "extra_copies": [], "notes": "Game Boy Advance BIOS (optional, HLE available)"},
    # --- GB / GBC (optional) ---
    {"filename": "gb_bios.bin", "system": "GB", "md5": "32fbbd84168d3482956eb3c5051637f5", "required": False, "subdir": "", "extra_copies": [], "notes": "Game Boy BIOS (optional)"},
    {"filename": "gbc_bios.bin", "system": "GBC", "md5": "dbfce9db9deaa2567f6a84fde55f9680", "required": False, "subdir": "", "extra_copies": [], "notes": "Game Boy Color BIOS (optional)"},
]

DARKOS_BIOS_FILES = [
    # --- PlayStation (required) ---
    {"filename": "scph5501.bin", "system": "PlayStation", "md5": "490f666e1afb15b7362b406ed1cea246", "required": True, "subdir": "", "extra_copies": [], "notes": "PS1 BIOS (North America)"},
    {"filename": "scph1001.bin", "system": "PlayStation", "md5": "924e392ed05558ffdb115408c263dccf", "required": True, "subdir": "", "extra_copies": [], "notes": "PS1 BIOS (North America, original)"},
    {"filename": "scph5500.bin", "system": "PlayStation", "md5": "8dd7d5296a650fac7319bce665a6a53c", "required": True, "subdir": "", "extra_copies": [], "notes": "PS1 BIOS (Japan)"},
    {"filename": "scph5502.bin", "system": "PlayStation", "md5": "32736f17079d0b2b7024407c39bd3050", "required": True, "subdir": "", "extra_copies": [], "notes": "PS1 BIOS (Europe)"},
    # --- Neo Geo (required) ---
    {"filename": "neogeo.zip", "system": "Neo Geo", "md5": "", "required": True, "subdir": "", "extra_copies": [], "notes": "Neo Geo BIOS"},
    # --- Sega CD (required) ---
    {"filename": "bios_CD_U.bin", "system": "Sega CD", "md5": "2efd74e3232ff260e371b99f84024f7f", "required": True, "subdir": "", "extra_copies": [], "notes": "Sega CD BIOS (North America)"},
    {"filename": "bios_CD_E.bin", "system": "Sega CD", "md5": "e66fa1dc5820d254611fdcdba0662372", "required": True, "subdir": "", "extra_copies": [], "notes": "Sega CD BIOS (Europe)"},
    {"filename": "bios_CD_J.bin", "system": "Sega CD", "md5": "278a9397d192149e84e820ac621a8edd", "required": True, "subdir": "", "extra_copies": [], "notes": "Sega CD BIOS (Japan)"},
    # --- TurboGrafx-CD (required) ---
    {"filename": "syscard3.pce", "system": "TurboGrafx-CD", "md5": "38179df8f4ac870017db21ebcbf53114", "required": True, "subdir": "", "extra_copies": [], "notes": "TurboGrafx-CD System Card 3"},
    # --- Sega Saturn (required) ---
    {"filename": "mpr-17933.bin", "system": "Saturn", "md5": "3240872c70984b6cbfda1586cab68dbe", "required": True, "subdir": "", "extra_copies": [], "notes": "Sega Saturn BIOS (Europe)"},
    # --- Dreamcast (optional, subdir dc/) ---
    {"filename": "dc_boot.bin", "system": "Dreamcast", "md5": "", "required": False, "subdir": "dc", "extra_copies": [], "notes": "Dreamcast BIOS"},
    {"filename": "dc_flash.bin", "system": "Dreamcast", "md5": "", "required": False, "subdir": "dc", "extra_copies": [], "notes": "Dreamcast Flash ROM"},
    # --- Neo Geo CD (optional) ---
    {"filename": "neocd_f.rom", "system": "Neo Geo CD", "md5": "", "required": False, "subdir": "neocd", "extra_copies": [], "notes": "Neo Geo CD front loader BIOS"},
    {"filename": "000-lo.lo", "system": "Neo Geo CD", "md5": "", "required": False, "subdir": "neocd", "extra_copies": [], "notes": "Neo Geo CD load order file"},
    # --- GBA (optional) ---
    {"filename": "gba_bios.bin", "system": "GBA", "md5": "a860e8c0b6d573d191e4ec7db1b1e4f6", "required": False, "subdir": "", "extra_copies": [], "notes": "Game Boy Advance BIOS (optional)"},
    # --- GB / GBC (optional) ---
    {"filename": "gb_bios.bin", "system": "GB", "md5": "32fbbd84168d3482956eb3c5051637f5", "required": False, "subdir": "", "extra_copies": [], "notes": "Game Boy BIOS (optional)"},
    {"filename": "gbc_bios.bin", "system": "GBC", "md5": "dbfce9db9deaa2567f6a84fde55f9680", "required": False, "subdir": "", "extra_copies": [], "notes": "Game Boy Color BIOS (optional)"},
]

MINUI_BIOS_FILES = [
    # --- PlayStation (required) ---
    {"filename": "scph1001.bin", "system": "PlayStation", "md5": "924e392ed05558ffdb115408c263dccf", "required": True, "subdir": "", "extra_copies": [], "notes": "PS1 BIOS (North America)"},
    {"filename": "scph5500.bin", "system": "PlayStation", "md5": "8dd7d5296a650fac7319bce665a6a53c", "required": True, "subdir": "", "extra_copies": [], "notes": "PS1 BIOS (Japan)"},
    {"filename": "scph5501.bin", "system": "PlayStation", "md5": "490f666e1afb15b7362b406ed1cea246", "required": True, "subdir": "", "extra_copies": [], "notes": "PS1 BIOS (North America)"},
    {"filename": "scph5502.bin", "system": "PlayStation", "md5": "32736f17079d0b2b7024407c39bd3050", "required": True, "subdir": "", "extra_copies": [], "notes": "PS1 BIOS (Europe)"},
    # --- Neo Geo (required) ---
    {"filename": "neogeo.zip", "system": "Neo Geo", "md5": "", "required": True, "subdir": "", "extra_copies": [], "notes": "Neo Geo BIOS"},
    # --- Sega CD (required) ---
    {"filename": "bios_CD_U.bin", "system": "Sega CD", "md5": "2efd74e3232ff260e371b99f84024f7f", "required": True, "subdir": "", "extra_copies": [], "notes": "Sega CD BIOS (North America)"},
    {"filename": "bios_CD_E.bin", "system": "Sega CD", "md5": "e66fa1dc5820d254611fdcdba0662372", "required": True, "subdir": "", "extra_copies": [], "notes": "Sega CD BIOS (Europe)"},
    {"filename": "bios_CD_J.bin", "system": "Sega CD", "md5": "278a9397d192149e84e820ac621a8edd", "required": True, "subdir": "", "extra_copies": [], "notes": "Sega CD BIOS (Japan)"},
    # --- TurboGrafx-CD (required) ---
    {"filename": "syscard3.pce", "system": "TurboGrafx-CD", "md5": "38179df8f4ac870017db21ebcbf53114", "required": True, "subdir": "", "extra_copies": [], "notes": "TurboGrafx-CD System Card 3"},
    # --- Saturn (required) ---
    {"filename": "mpr-17933.bin", "system": "Saturn", "md5": "3240872c70984b6cbfda1586cab68dbe", "required": True, "subdir": "", "extra_copies": [], "notes": "Sega Saturn BIOS (Europe)"},
    # --- GBA (optional) ---
    {"filename": "gba_bios.bin", "system": "GBA", "md5": "a860e8c0b6d573d191e4ec7db1b1e4f6", "required": False, "subdir": "", "extra_copies": [], "notes": "Game Boy Advance BIOS (optional)"},
    # --- GB / GBC (optional) ---
    {"filename": "gb_bios.bin", "system": "GB", "md5": "32fbbd84168d3482956eb3c5051637f5", "required": False, "subdir": "", "extra_copies": [], "notes": "Game Boy BIOS (optional)"},
    {"filename": "gbc_bios.bin", "system": "GBC", "md5": "dbfce9db9deaa2567f6a84fde55f9680", "required": False, "subdir": "", "extra_copies": [], "notes": "Game Boy Color BIOS (optional)"},
]

ROCKNIX_BIOS_FILES = [
    # --- PlayStation (required) ---
    {"filename": "scph5500.bin", "system": "PlayStation", "md5": "8dd7d5296a650fac7319bce665a6a53c", "required": True, "subdir": "", "extra_copies": [], "notes": "PS1 BIOS (Japan)"},
    {"filename": "scph5501.bin", "system": "PlayStation", "md5": "490f666e1afb15b7362b406ed1cea246", "required": True, "subdir": "", "extra_copies": [], "notes": "PS1 BIOS (North America)"},
    {"filename": "scph5502.bin", "system": "PlayStation", "md5": "32736f17079d0b2b7024407c39bd3050", "required": True, "subdir": "", "extra_copies": [], "notes": "PS1 BIOS (Europe)"},
    # --- Neo Geo (required) ---
    {"filename": "neogeo.zip", "system": "Neo Geo", "md5": "", "required": True, "subdir": "", "extra_copies": [], "notes": "Neo Geo BIOS"},
    # --- Sega CD (required) ---
    {"filename": "bios_CD_U.bin", "system": "Sega CD", "md5": "2efd74e3232ff260e371b99f84024f7f", "required": True, "subdir": "", "extra_copies": [], "notes": "Sega CD BIOS (North America)"},
    {"filename": "bios_CD_E.bin", "system": "Sega CD", "md5": "e66fa1dc5820d254611fdcdba0662372", "required": True, "subdir": "", "extra_copies": [], "notes": "Sega CD BIOS (Europe)"},
    {"filename": "bios_CD_J.bin", "system": "Sega CD", "md5": "278a9397d192149e84e820ac621a8edd", "required": True, "subdir": "", "extra_copies": [], "notes": "Sega CD BIOS (Japan)"},
    # --- TurboGrafx-CD (required) ---
    {"filename": "syscard3.pce", "system": "TurboGrafx-CD", "md5": "38179df8f4ac870017db21ebcbf53114", "required": True, "subdir": "", "extra_copies": [], "notes": "TurboGrafx-CD System Card 3"},
    # --- Sega Saturn (required) ---
    {"filename": "mpr-17933.bin", "system": "Saturn", "md5": "3240872c70984b6cbfda1586cab68dbe", "required": True, "subdir": "", "extra_copies": [], "notes": "Sega Saturn BIOS (Europe)"},
    # --- Dreamcast (optional, subdir dc/) ---
    {"filename": "dc_boot.bin", "system": "Dreamcast", "md5": "", "required": False, "subdir": "dc", "extra_copies": [], "notes": "Dreamcast BIOS"},
    {"filename": "dc_flash.bin", "system": "Dreamcast", "md5": "", "required": False, "subdir": "dc", "extra_copies": [], "notes": "Dreamcast Flash ROM"},
    # --- Neo Geo CD (optional) ---
    {"filename": "neocdz.zip", "system": "Neo Geo CD", "md5": "", "required": False, "subdir": "neocd", "extra_copies": [], "notes": "Neo Geo CDZ BIOS"},
    # --- GBA (optional) ---
    {"filename": "gba_bios.bin", "system": "GBA", "md5": "a860e8c0b6d573d191e4ec7db1b1e4f6", "required": False, "subdir": "", "extra_copies": [], "notes": "Game Boy Advance BIOS (optional, HLE available)"},
    # --- GB / GBC (optional) ---
    {"filename": "gb_bios.bin", "system": "GB", "md5": "32fbbd84168d3482956eb3c5051637f5", "required": False, "subdir": "", "extra_copies": [], "notes": "Game Boy BIOS (optional)"},
    {"filename": "gbc_bios.bin", "system": "GBC", "md5": "dbfce9db9deaa2567f6a84fde55f9680", "required": False, "subdir": "", "extra_copies": [], "notes": "Game Boy Color BIOS (optional)"},
]

KORIKI_BIOS_FILES = [
    # --- PlayStation (required) ---
    {"filename": "scph1001.bin", "system": "PlayStation", "md5": "924e392ed05558ffdb115408c263dccf", "required": True, "subdir": "", "extra_copies": [], "notes": "PS1 BIOS (North America)"},
    {"filename": "scph5500.bin", "system": "PlayStation", "md5": "8dd7d5296a650fac7319bce665a6a53c", "required": True, "subdir": "", "extra_copies": [], "notes": "PS1 BIOS (Japan)"},
    {"filename": "scph5501.bin", "system": "PlayStation", "md5": "490f666e1afb15b7362b406ed1cea246", "required": True, "subdir": "", "extra_copies": [], "notes": "PS1 BIOS (North America)"},
    {"filename": "scph5502.bin", "system": "PlayStation", "md5": "32736f17079d0b2b7024407c39bd3050", "required": True, "subdir": "", "extra_copies": [], "notes": "PS1 BIOS (Europe)"},
    # --- Neo Geo (required) ---
    {"filename": "neogeo.zip", "system": "Neo Geo", "md5": "", "required": True, "subdir": "", "extra_copies": ["Roms/NEOGEO/neogeo.zip"], "notes": "Neo Geo BIOS (also needed in Roms/NEOGEO/)"},
    # --- Sega CD (required) ---
    {"filename": "bios_CD_U.bin", "system": "Sega CD", "md5": "2efd74e3232ff260e371b99f84024f7f", "required": True, "subdir": "", "extra_copies": [], "notes": "Sega CD BIOS (North America)"},
    {"filename": "bios_CD_E.bin", "system": "Sega CD", "md5": "e66fa1dc5820d254611fdcdba0662372", "required": True, "subdir": "", "extra_copies": [], "notes": "Sega CD BIOS (Europe)"},
    {"filename": "bios_CD_J.bin", "system": "Sega CD", "md5": "278a9397d192149e84e820ac621a8edd", "required": True, "subdir": "", "extra_copies": [], "notes": "Sega CD BIOS (Japan)"},
    # --- TurboGrafx-CD (required) ---
    {"filename": "syscard3.pce", "system": "TurboGrafx-CD", "md5": "38179df8f4ac870017db21ebcbf53114", "required": True, "subdir": "", "extra_copies": [], "notes": "TurboGrafx-CD / PC Engine CD System Card 3"},
    # --- FDS (optional) ---
    {"filename": "disksys.rom", "system": "FDS", "md5": "", "required": False, "subdir": "", "extra_copies": [], "notes": "Famicom Disk System BIOS"},
    # --- Atari 5200 (optional) ---
    {"filename": "5200.rom", "system": "Atari 5200", "md5": "", "required": False, "subdir": "", "extra_copies": [], "notes": "Atari 5200 BIOS"},
    # --- Atari Lynx (optional) ---
    {"filename": "lynxboot.img", "system": "Atari Lynx", "md5": "", "required": False, "subdir": "", "extra_copies": [], "notes": "Atari Lynx boot ROM"},
    # --- Pokemon Mini (optional) ---
    {"filename": "bios.min", "system": "Pokemon Mini", "md5": "", "required": False, "subdir": "", "extra_copies": [], "notes": "Pokemon Mini BIOS"},
    # --- GBA (optional) ---
    {"filename": "gba_bios.bin", "system": "GBA", "md5": "a860e8c0b6d573d191e4ec7db1b1e4f6", "required": False, "subdir": "", "extra_copies": [], "notes": "Game Boy Advance BIOS (optional, HLE available)"},
    # --- GB / GBC (optional) ---
    {"filename": "gb_bios.bin", "system": "GB", "md5": "32fbbd84168d3482956eb3c5051637f5", "required": False, "subdir": "", "extra_copies": [], "notes": "Game Boy BIOS (optional)"},
    {"filename": "gbc_bios.bin", "system": "GBC", "md5": "dbfce9db9deaa2567f6a84fde55f9680", "required": False, "subdir": "", "extra_copies": [], "notes": "Game Boy Color BIOS (optional)"},
]

# ---------------------------------------------------------------------------
# OS Profile definitions
# ---------------------------------------------------------------------------

OS_PROFILES = {
    "onion": {
        "name": "Onion OS",
        "device": "Miyoo Mini / Mini+",
        "description": (
            "\u201cAn enhanced operating system for your Miyoo Mini and Mini+, "
            "featuring fine-tuned emulation with 100+ built-in emulators, "
            "auto-save and resume, a wealth of customization options, "
            "and much more.\u201d"
        ),
        "description_source": "https://github.com/OnionUI/Onion",
        "compatible_devices": [
            "Miyoo Mini",
            "Miyoo Mini+",
        ],
        "install_notes": (
            "Extract the release zip to a FAT32 formatted SD card. "
            "You can install fresh (with format) or upgrade in-place "
            "without losing your ROMs and saves. "
            "Recommended SD card size: 16 GB or larger. "
            "After installation, add your ROMs to the Roms folder "
            "and BIOS files to the BIOS folder."
        ),
        "install_method": "zip_extract",
        "releases_url": "https://api.github.com/repos/OnionUI/Onion/releases",
        "project_url": "https://github.com/OnionUI/Onion",
        "wiki_url": "https://onionui.github.io/docs",
        "sd_label": "ONION",
        "expected_dirs": [".tmp_update", "BIOS", "RetroArch", "miyoo", "Themes"],
        "detect_markers": [".tmp_update"],
        "version_paths": [".tmp_update/onionVersion/version.txt"],
        "bios_dir": "BIOS",
        "bios_files": ONION_BIOS_FILES,
        "asset_filter": None,
        "cluster_sectors": lambda size_bytes: "128" if size_bytes > 137_438_953_472 else "64",
    },
    "crossmix": {
        "name": "CrossMix OS",
        "device": "TrimUI Smart Pro",
        "description": (
            "\u201cCrossMix-OS, the OS which elevates your TrimUI Smart Pro "
            "to new heights. CrossMix-OS uses TrimUI Stock user interface "
            "with refined configurations, new features, new emulators "
            "and new apps.\u201d"
        ),
        "description_source": "https://github.com/cizia64/CrossMix-OS",
        "compatible_devices": [
            "TrimUI Smart Pro",
        ],
        "install_notes": (
            "Extract the release zip to a FAT32 formatted SD card. "
            "You can install fresh (with format) or upgrade in-place "
            "without losing your ROMs and saves. "
            "Recommended SD card size: 32 GB or larger. "
            "After installation, add your ROMs to the Roms folder "
            "and BIOS files to the BIOS folder."
        ),
        "install_method": "zip_extract",
        "releases_url": "https://api.github.com/repos/cizia64/CrossMix-OS/releases",
        "project_url": "https://github.com/cizia64/CrossMix-OS",
        "wiki_url": "https://github.com/cizia64/CrossMix-OS/wiki",
        "sd_label": "CROSSMIX",
        "expected_dirs": ["System", "Emus", "Apps", "BIOS", "Roms", "RetroArch"],
        "detect_markers": ["System", "Emus"],
        "version_paths": [
            "System/usr/trimui/crossmix_version.txt",
            "System/crossmix_version.txt",
        ],
        "bios_dir": "BIOS",
        "bios_files": CROSSMIX_BIOS_FILES,
        "asset_filter": None,
        "cluster_sectors": lambda size_bytes: (
            "64" if size_bytes < 128 * 1024**3 else
            "128" if size_bytes < 256 * 1024**3 else
            "256" if size_bytes < 512 * 1024**3 else
            "512" if size_bytes < 1024 * 1024**3 else
            "1024"
        ),
    },
    "minui": {
        "name": "MinUI",
        "device": "Multiple (Miyoo, TrimUI, Anbernic, etc.)",
        "description": (
            "\u201cMinUI is a focused, custom launcher and libretro frontend "
            "for a variety of retro handhelds.\u201d\n\n"
            "Note: This repo is archived. See MyMinUI for active development."
        ),
        "description_source": "https://github.com/shauninman/MinUI",
        "compatible_devices": [
            "Miyoo Mini / Mini+",
            "Miyoo A30",
            "Miyoo Flip",
            "TrimUI Smart",
            "TrimUI Smart Pro / Brick",
            "Anbernic RG35XX (2023)",
            "Anbernic RG35XX Plus / H / SP",
            "Anbernic RG40XX H / V",
            "Anbernic RG CubeXX",
            "Anbernic RG34XX / RG34XX SP",
            "Anbernic RG28XX",
            "Powkiddy RGB30",
            "GKD Pixel",
            "M17",
            "MagicX XU Mini M",
            "MagicX Mini Zero 28",
        ],
        "install_notes": (
            "MinUI releases contain TWO zips per release:\n\n"
            "1. BASE (required) \u2014 Install this first. Contains the core "
            "system, main emulators (NES, SNES, Game Boy, Genesis, PS1, "
            "and more), and boot files for all supported devices.\n\n"
            "2. EXTRAS (optional) \u2014 Install on top of base. Adds extra "
            "emulators (Game Gear, Master System, Neo Geo Pocket, "
            "TurboGrafx-16, Virtual Boy, Pico-8, Super Game Boy, mGBA, "
            "Pokemon mini), additional tools, and BIOS files.\n\n"
            "Extract each zip to a FAT32 formatted SD card. The base zip "
            "includes platform boot folders for all supported devices; the "
            "correct one is used automatically. The .system directory is "
            "created on first boot."
        ),
        "install_method": "zip_extract",
        "releases_url": "https://api.github.com/repos/shauninman/MinUI/releases",
        "project_url": "https://github.com/shauninman/MinUI",
        "wiki_url": "https://github.com/shauninman/MinUI#readme",
        "sd_label": "MINUI",
        "expected_dirs": ["Bios", "Roms", "Saves", "trimui"],
        "detect_markers": ["MinUI.zip", "trimui"],
        "version_paths": [".system/version.txt"],
        "bios_dir": "Bios",
        "bios_files": MINUI_BIOS_FILES,
        "asset_filter": r"\.zip$",
        "cluster_sectors": lambda size_bytes: "64",
    },
    "myminui": {
        "name": "MyMinUI",
        "device": "Multiple (Miyoo, TrimUI, Anbernic, R36S, etc.)",
        "description": (
            "\u201cMyMinUI is a fork of the latest MinUI, I like MinUI but "
            "I also like playing old arcade coin up (thanks to FinUI) and "
            "DOOM which were missing so I added them.\u201d"
        ),
        "description_source": "https://github.com/Turro75/MyMinUI",
        "compatible_devices": [
            "Miyoo Mini / Mini+",
            "Miyoo A30",
            "Anbernic RG35XX (2023)",
            "R36S / R36H / R36S Plus",
            "R40XX / XF40H",
            "SJGAM M21 / M22pro",
        ],
        "install_notes": (
            "Each release contains one zip per supported platform. "
            "Download the zip matching your device and extract it to a "
            "FAT32 formatted SD card. Unlike original MinUI, MyMinUI "
            "releases are device-specific \u2014 make sure to pick the "
            "correct one for your handheld."
        ),
        "install_method": "zip_extract",
        "releases_url": "https://api.github.com/repos/Turro75/MyMinUI/releases",
        "project_url": "https://github.com/Turro75/MyMinUI",
        "wiki_url": "https://github.com/Turro75/MyMinUI#readme",
        "sd_label": "MINUI",
        "expected_dirs": ["Bios", "Roms", "Saves"],
        "detect_markers": ["MinUI.zip"],
        "version_paths": [".system/version.txt"],
        "bios_dir": "Bios",
        "bios_files": MINUI_BIOS_FILES,
        "asset_filter": r"\.zip$",
        "cluster_sectors": lambda size_bytes: "64",
    },
    "darkos": {
        "name": "dArkOS",
        "device": "Anbernic RG353/RG503, Powkiddy RGB, ODROID",
        "description": (
            "\u201cDebian based version of the ArkOS operating system for "
            "select RK3326 and RK3566 based portable gaming devices.\u201d"
        ),
        "description_source": "https://github.com/christianhaitian/dArkOS",
        "compatible_devices": [
            "Anbernic RG353V / RG353VS / RG353M",
            "Anbernic RG503",
            "Anbernic RG351P / RG351M / RG351V / RG351MP",
            "Powkiddy RGB10 / RGB20 Pro / RGB30",
            "Powkiddy RK2023",
            "ODROID Go Advance / Go Super",
            "G350",
            "A10 Mini",
        ],
        "install_notes": (
            "dArkOS uses raw disk images flashed directly to the SD card "
            "(similar to Raspberry Pi OS). This erases ALL existing data on "
            "the card. Each device has its own image \u2014 select the correct "
            "one for your handheld. Images are split into two parts (.001 + "
            ".002) which are downloaded and extracted automatically.\n\n"
            "First boot takes several minutes as the system expands the "
            "storage partition and converts it to exFAT. Do not interrupt "
            "this process. After setup, BIOS files can be installed to the "
            "EASYROMS partition using the BIOS Manager tab."
        ),
        "install_method": "raw_image",
        "releases_url": "https://api.github.com/repos/christianhaitian/dArkOS/releases",
        "project_url": "https://github.com/christianhaitian/dArkOS",
        "wiki_url": "https://github.com/christianhaitian/dArkOS/wiki",
        "sd_label": "",
        "expected_dirs": [],
        "detect_markers": [],
        "version_paths": [],
        "bios_dir": "bios",
        "bios_partition_label": "EASYROMS",
        "bios_files": DARKOS_BIOS_FILES,
        "asset_filter": r"\.img\.7z\.001$",
        "cluster_sectors": lambda size_bytes: "64",
    },
    "rocknix": {
        "name": "ROCKNIX",
        "device": "Anbernic, Powkiddy, AYANEO, Ayn, Retroid, etc.",
        "description": (
            "\u201cROCKNIX is an immutable Linux distribution for handheld "
            "gaming devices, built on Buildroot with EmulationStation as "
            "its frontend. It provides integrated RetroArch emulation, "
            "network play, RetroAchievements, cloud sync, and custom "
            "performance profiles.\u201d"
        ),
        "description_source": "https://github.com/ROCKNIX/distribution",
        "compatible_devices": [
            "Anbernic RG351P / RG351M / RG351V",
            "Anbernic RG353P / RG353M / RG353V / RG353VS",
            "Anbernic RG503 / RG552",
            "Anbernic RG ARC D / RG ARC S",
            "Anbernic RG35XX Plus / H / SP / 2024",
            "Anbernic RG28XX",
            "Anbernic RG40XX V / H",
            "Anbernic RG CubeXX",
            "Anbernic RG34XX / RG34XX SP",
            "AYANEO Pocket ACE / DMG / EVO / S2",
            "Ayn Odin 2 / Odin 2 Mini / Odin 2 Portal",
            "GameForce Ace",
            "Hardkernel ODROID Go Advance / Go Super / Go Ultra",
            "MagicX XU Mini M",
            "Powkiddy RGB10 / RGB10 Max 3 Pro / RGB10X",
            "Powkiddy RK2023 / RGB20SX / RGB20 Pro / RGB30",
            "Powkiddy X35S / X35H / X55 / XU10",
            "Retroid Pocket 5 / Pocket Mini / Pocket Flip 2",
            "R33S / R35S / R36S / K36",
        ],
        "install_notes": (
            "ROCKNIX uses raw disk images flashed directly to the SD card "
            "(similar to Raspberry Pi OS). This erases ALL existing data on "
            "the card. Each device has its own image \u2014 select the correct "
            "one for your handheld. Use Rufus, balenaEtcher, Raspberry Pi "
            "Imager, or dd to flash the image.\n\n"
            "First boot runs an install/expansion process and reboots into "
            "EmulationStation. Do not interrupt this process. After setup, "
            "BIOS files can be installed to the STORAGE partition under "
            "roms/bios/ using the BIOS Manager tab."
        ),
        "install_method": "raw_image",
        "releases_url": "https://api.github.com/repos/ROCKNIX/distribution/releases",
        "project_url": "https://github.com/ROCKNIX/distribution",
        "wiki_url": "https://rocknix.org/",
        "sd_label": "",
        "expected_dirs": [],
        "detect_markers": [],
        "version_paths": [],
        "bios_dir": "roms/bios",
        "bios_partition_label": "STORAGE",
        "bios_files": ROCKNIX_BIOS_FILES,
        "asset_filter": r"\.img\.gz$",
        "cluster_sectors": lambda size_bytes: "64",
    },
    "koriki": {
        "name": "Koriki",
        "device": "Miyoo Mini",
        "description": (
            "\u201cKoriki is a software compilation for the microSD card slot "
            "of Miyoo Mini retro console. It runs over stock firmware and "
            "brings mainly the SimpleMenu frontend to this device.\u201d"
        ),
        "description_source": "https://github.com/Rparadise-Team/Koriki",
        "compatible_devices": [
            "Miyoo Mini v1",
            "Miyoo Mini v2",
            "Miyoo Mini v3",
            "Miyoo Mini v4",
            "Miyoo Mini+",
            "Miyoo Mini Flip",
        ],
        "install_notes": (
            "Extract the full release zip to a FAT32 formatted SD card. "
            "Koriki runs on top of the Miyoo Mini stock firmware and uses "
            "SimpleMenu as its frontend. "
            "Recommended SD card size: 16 GB or larger. "
            "After installation, add your ROMs to the Roms folder "
            "and BIOS files to the BIOS folder."
        ),
        "install_method": "zip_extract",
        "releases_url": "https://api.github.com/repos/Rparadise-Team/Koriki/releases",
        "project_url": "https://github.com/Rparadise-Team/Koriki",
        "wiki_url": "https://github.com/Rparadise-Team/Koriki#readme",
        "sd_label": "",
        "expected_dirs": ["Koriki", ".simplemenu", "BIOS", "RetroArch", "Roms", "Saves"],
        "detect_markers": ["Koriki", ".simplemenu"],
        "version_paths": ["Koriki/version.txt"],
        "bios_dir": "BIOS",
        "bios_files": KORIKI_BIOS_FILES,
        "asset_filter": r"_full\.zip$",
        "cluster_sectors": lambda size_bytes: "64",
    },
}
