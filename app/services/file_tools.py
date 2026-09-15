import os
import shutil
from datetime import datetime

BACKUP_DIR = "backups"


def read_file(path: str) -> str:
    """Reads and returns the full contents of a file."""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def backup_file(path: str) -> str:
    """
    Copies the current version of a file into a timestamped backup folder
    before any edit is applied. Returns the backup path.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Cannot back up — file does not exist: {path}")

    os.makedirs(BACKUP_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = path.replace("\\", "_").replace("/", "_")
    backup_path = os.path.join(BACKUP_DIR, f"{safe_name}.{timestamp}.bak")

    shutil.copy2(path, backup_path)
    return backup_path


def write_file(path: str, content: str) -> str | None:
    """
    If the file already exists, backs it up first, then overwrites it.
    If the file is new, just creates it (nothing to back up).
    Returns the backup path if one was made, else None.
    """
    backup_path = backup_file(path) if os.path.exists(path) else None

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

    return backup_path


def restore_backup(backup_path: str, original_path: str):
    """Restores a file from a specific backup, in case a patch made things worse."""
    shutil.copy2(backup_path, original_path)