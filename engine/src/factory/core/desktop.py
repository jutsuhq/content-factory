"""Hand a finished file to the desktop: show it in Finder or Explorer, open it in the default player, or put the file
itself on the clipboard so it pastes into a messenger or a folder."""

from __future__ import annotations

import os
import platform
import subprocess
from pathlib import Path

SYSTEM = platform.system()


def reveal(path: Path) -> None:
    if SYSTEM == "Darwin":
        subprocess.run(["open", "-R", str(path)], check=True)
    elif SYSTEM == "Windows":
        subprocess.run(["explorer", f"/select,{path}"], check=False)  # explorer exits with 1 even when it worked
    else:
        subprocess.run(["xdg-open", str(path.parent)], check=True)


def open_file(path: Path) -> None:
    if SYSTEM == "Darwin":
        subprocess.run(["open", str(path)], check=True)
    elif SYSTEM == "Windows":
        os.startfile(path)  # type: ignore[attr-defined]  # Windows only
    else:
        subprocess.run(["xdg-open", str(path)], check=True)


def copy_file(path: Path) -> None:
    """The file, not its path: pasting gives the video itself."""
    if SYSTEM == "Darwin":
        quoted = str(path).replace("\\", "\\\\").replace('"', '\\"')
        subprocess.run(["osascript", "-e", f'set the clipboard to (POSIX file "{quoted}")'], check=True)
    elif SYSTEM == "Windows":
        literal = str(path).replace("'", "''")
        subprocess.run(["powershell", "-NoProfile", "-Command", f"Set-Clipboard -LiteralPath '{literal}'"], check=True)
    else:
        raise RuntimeError("copying a file to the clipboard works on macOS and Windows")


def choose_folder(start: Path) -> Path | None:
    """The system folder picker, in front of the app; None when cancelled."""
    if SYSTEM == "Darwin":
        default = str(start).replace("\\", "\\\\").replace('"', '\\"')
        script = (
            "tell application (path to frontmost application as text) to POSIX path of "
            f'(choose folder with prompt "Save finished videos to" default location POSIX file "{default}")'
        )
        r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, check=False)
    elif SYSTEM == "Windows":
        ps = (
            "Add-Type -AssemblyName System.Windows.Forms; $d = New-Object System.Windows.Forms.FolderBrowserDialog; "
            f"$d.SelectedPath = '{str(start).replace(chr(39), chr(39) * 2)}'; "
            "if ($d.ShowDialog() -eq 'OK') { $d.SelectedPath }"
        )
        r = subprocess.run(
            ["powershell", "-NoProfile", "-STA", "-Command", ps], capture_output=True, text=True, check=False
        )
    else:
        r = subprocess.run(
            ["zenity", "--file-selection", "--directory", f"--filename={start}/"],
            capture_output=True,
            text=True,
            check=False,
        )
    path = r.stdout.strip()
    return Path(path) if r.returncode == 0 and path else None
