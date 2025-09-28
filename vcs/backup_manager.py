#!/usr/bin/env python3
"""
Backup Manager for Lyne VCS

Manages rolling backups (last 10 edits) for file recovery.
"""

import os
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from util.logging import get_logger, log_function_call, log_warning

logger = get_logger("backup_manager")


class BackupManager:
    """Manages rolling backups for file version control."""

    def __init__(self, project_path: str = None):
        """Initialize backup manager for the project."""
        if project_path is None:
            import os
            operating_path = os.environ.get('LYNE_OPERATING_PATH')
            if operating_path:
                self.project_path = Path(operating_path).resolve()
            else:
                self.project_path = Path.cwd()
        else:
            self.project_path = Path(project_path).resolve()

        self.backup_dir = self.project_path / "time_machine"
        self.backup_index_file = self.backup_dir / "backup_index.json"
        self.max_backups_per_file = 10
        self.deleted_files_retention_days = 7
        self._migrate_old_backups()
        self._load_backup_index()
        self._cleanup_expired_deleted_files()

    def _ensure_backup_directory(self):
        """Create backup directory if it doesn't exist with super hiding."""
        try:
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            if os.name == 'nt':
                import ctypes
                ctypes.windll.kernel32.SetFileAttributesW(
                    str(self.backup_dir), 0x02 | 0x04)
        except Exception as e:
            log_error(e, "Failed to create backup directory", logger)

    def _migrate_old_backups(self):
        """Migrate from old .lyne_backup to new time_machine directory."""
        try:
            old_backup_dir = self.project_path / ".lyne_backup"
            if old_backup_dir.exists() and old_backup_dir != self.backup_dir:
                import shutil
                for item in old_backup_dir.iterdir():
                    if item.is_file():
                        shutil.copy2(item, self.backup_dir / item.name)

                old_index_file = old_backup_dir / "backup_index.json"
                if old_index_file.exists():
                    try:
                        with open(old_index_file, 'r', encoding='utf-8') as f:
                            old_index = json.load(f)

                        if self.backup_index_file.exists():

                            with open(self.backup_index_file, 'r', encoding='utf-8') as f:
                                new_index = json.load(f)

                            for file_path, backups in old_index.get("files", {}).items():
                                if file_path not in new_index.get("files", {}):
                                    new_index["files"][file_path] = backups
                            with open(self.backup_index_file, 'w', encoding='utf-8') as f:
                                json.dump(new_index, f, indent=2,
                                          ensure_ascii=False)
                        else:

                            shutil.copy2(old_index_file,
                                         self.backup_index_file)

                    except Exception as e:
                        log_error(e, "Failed to migrate backup index", logger)

                try:
                    shutil.rmtree(old_backup_dir)
                    log_success(
                        "Migrated from .lyne_backup to time_machine", logger)
                except Exception as e:
                    log_error(
                        e, "Failed to remove old backup directory", logger)

        except Exception as e:
            log_error(e, "Failed to migrate old backups", logger)

    def _load_backup_index(self):
        """Load the backup index from file."""
        self.backup_index = {"files": {}, "last_updated": None}

        if self.backup_index_file.exists():
            try:
                with open(self.backup_index_file, 'r', encoding='utf-8') as f:
                    self.backup_index = json.load(f)
            except Exception as e:
                log_error(e, "Failed to load backup index", logger)

    def _save_backup_index(self):
        """Save the backup index to file."""
        try:
            self.backup_index["last_updated"] = datetime.now().isoformat()
            with open(self.backup_index_file, 'w', encoding='utf-8') as f:
                json.dump(self.backup_index, f, indent=2, ensure_ascii=False)
        except Exception as e:
            log_error(e, "Failed to save backup index", logger)

    def _get_backup_path(self, file_path: str, version_num: int) -> Path:
        """Get the backup file path for a specific version."""

        safe_name = file_path.replace(
            '/', '_').replace('\\', '_').replace(':', '_')
        return self.backup_dir / f"backup_{safe_name}_v{version_num}.txt"

    def _get_file_hash(self, file_path: str) -> Optional[str]:
        """Get hash of file content."""
        try:
            if not Path(file_path).exists():
                return None

            with open(file_path, 'rb') as f:
                content = f.read()

            if len(content) > 10_000_000:
                return None

            return hashlib.md5(content).hexdigest()
        except Exception:
            return None

    def backup_file(self, file_path: str) -> bool:
        """
        Create a backup of the specified file.

        Args:
            file_path: Path to the file to backup

        Returns:
            True if backup was created, False otherwise
        """
        try:
            log_function_call("backup_file", {"file_path": file_path}, logger)

            file_path = str(Path(file_path).resolve())
            file_hash = self._get_file_hash(file_path)

            if not file_hash:
                return False

            if file_path in self.backup_index["files"]:
                last_backup = self.backup_index["files"][file_path][-1] if self.backup_index["files"][file_path] else None
                if last_backup and last_backup.get("hash") == file_hash:
                    return False

            if file_path not in self.backup_index["files"]:
                self.backup_index["files"][file_path] = []

            backups = self.backup_index["files"][file_path]

            if len(backups) >= self.max_backups_per_file:

                oldest_backup = backups.pop(0)
                backup_file_path = self._get_backup_path(
                    file_path, oldest_backup["version"])
                try:
                    backup_file_path.unlink(missing_ok=True)
                except Exception:
                    pass

            version_num = len(backups) + 1
            backup_file_path = self._get_backup_path(file_path, version_num)

            try:
                with open(file_path, 'r', encoding='utf-8', errors='replace') as src:
                    content = src.read()

                with open(backup_file_path, 'w', encoding='utf-8') as dst:
                    dst.write(content)

            except Exception as e:
                log_error(
                    e, f"Failed to create backup file: {backup_file_path}", logger)
                return False

            backup_info = {
                "version": version_num,
                "timestamp": datetime.now().isoformat(),
                "hash": file_hash,
                "size": len(content)
            }

            backups.append(backup_info)
            self._save_backup_index()

            log_success(
                f"Backup created for {file_path} (version {version_num})", logger)
            return True

        except Exception as e:
            log_error(e, f"Failed to backup file: {file_path}", logger)
            return False

    def get_file_versions(self, file_path: str) -> List[Dict]:
        """
        Get list of available versions for a file.

        Args:
            file_path: Path to the file

        Returns:
            List of version dictionaries
        """
        file_path = str(Path(file_path).resolve())
        return self.backup_index["files"].get(file_path, [])

    def get_backup_content(self, file_path: str, version_num: int) -> Optional[str]:
        """
        Get content of a specific backup version.

        Args:
            file_path: Path to the file
            version_num: Version number to retrieve

        Returns:
            Content of the backup, or None if not found
        """
        try:
            backup_path = self._get_backup_path(file_path, version_num)
            if backup_path.exists():
                with open(backup_path, 'r', encoding='utf-8', errors='replace') as f:
                    return f.read()
            return None
        except Exception as e:
            log_error(
                e, f"Failed to read backup content: {file_path} v{version_num}", logger)
            return None

    def revert_file(self, file_path: str, version_num: int) -> bool:
        """
        Revert file to a specific version.

        Args:
            file_path: Path to the file to revert
            version_num: Version number to revert to

        Returns:
            True if revert was successful, False otherwise
        """
        try:
            log_function_call("revert_file", {
                "file_path": file_path,
                "version_num": version_num
            }, logger)

            backup_content = self.get_backup_content(file_path, version_num)
            if not backup_content:
                return False

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(backup_content)

            log_success(
                f"File reverted: {file_path} to version {version_num}", logger)
            return True

        except Exception as e:
            log_error(e, f"Failed to revert file: {file_path}", logger)
            return False

    def get_all_backed_files(self) -> List[str]:
        """Get list of all files that have backups."""
        return list(self.backup_index["files"].keys())

    def backup_deleted_file(self, file_path: str) -> bool:
        """
        Backup a file before it's deleted.

        Args:
            file_path: Path to the file being deleted

        Returns:
            True if backup was created, False otherwise
        """
        try:
            log_function_call("backup_deleted_file", {
                              "file_path": file_path}, logger)

            file_path = str(Path(file_path).resolve())

            try:
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
                file_size = len(content)
            except Exception as e:
                log_error(
                    e, f"Failed to read file content for deletion backup: {file_path}", logger)
                return False

            if file_size > 10_000_000:
                log_warning(
                    f"Skipping backup of large file: {file_path} ({file_size} bytes)", logger)
                return False

            import hashlib
            import time
            timestamp = str(int(time.time()))
            file_hash = hashlib.md5(content.encode('utf-8')).hexdigest()[:8]
            safe_name = file_path.replace(
                '/', '_').replace('\\', '_').replace(':', '_')
            backup_filename = f"deleted_{safe_name}_{timestamp}_{file_hash}.json"

            backup_file_path = self.backup_dir / backup_filename

            backup_data = {
                "original_path": file_path,
                "content": content,
                "size": file_size,
                "deleted_at": timestamp,
                "file_hash": file_hash
            }

            with open(backup_file_path, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)

            if "deleted_files" not in self.backup_index:
                self.backup_index["deleted_files"] = []

            self.backup_index["deleted_files"].append({
                "original_path": file_path,
                "backup_file": backup_filename,
                "deleted_at": timestamp,
                "size": file_size
            })

            self._save_backup_index()

            log_success(
                f"Backup created for deleted file: {file_path}", logger)
            return True

        except Exception as e:
            log_error(e, f"Failed to backup deleted file: {file_path}", logger)
            return False

    def restore_deleted_file(self, backup_filename: str) -> bool:
        """
        Restore a deleted file from backup.

        Args:
            backup_filename: Name of the backup file

        Returns:
            True if file was restored, False otherwise
        """
        try:
            log_function_call("restore_deleted_file", {
                              "backup_filename": backup_filename}, logger)

            backup_file_path = self.backup_dir / backup_filename

            if not backup_file_path.exists():
                log_error(Exception("Backup file not found"),
                          f"Backup file missing: {backup_filename}", logger)
                return False

            with open(backup_file_path, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)

            original_path = backup_data["original_path"]
            content = backup_data["content"]

            Path(original_path).parent.mkdir(parents=True, exist_ok=True)

            with open(original_path, 'w', encoding='utf-8') as f:
                f.write(content)

            if "deleted_files" in self.backup_index:
                self.backup_index["deleted_files"] = [
                    df for df in self.backup_index["deleted_files"]
                    if df.get("backup_file") != backup_filename
                ]

            backup_file_path.unlink(missing_ok=True)

            self._save_backup_index()

            log_success(f"Restored deleted file: {original_path}", logger)
            return True

        except Exception as e:
            log_error(
                e, f"Failed to restore deleted file: {backup_filename}", logger)
            return False

    def get_deleted_files(self) -> List[Dict]:
        """Get list of deleted files that can be restored."""
        return self.backup_index.get("deleted_files", [])

    def _cleanup_expired_deleted_files(self):
        """Clean up deleted files older than retention period."""
        try:
            import time
            current_time = time.time()
            retention_seconds = self.deleted_files_retention_days * 24 * 60 * 60

            if "deleted_files" not in self.backup_index:
                return

            kept_files = []
            for deleted_file in self.backup_index["deleted_files"]:
                deleted_at = float(deleted_file.get("deleted_at", 0))
                if current_time - deleted_at < retention_seconds:
                    kept_files.append(deleted_file)
                else:

                    backup_file = deleted_file.get("backup_file")
                    if backup_file:
                        backup_path = self.backup_dir / backup_file
                        backup_path.unlink(missing_ok=True)
                        log_success(
                            f"Cleaned up expired backup: {backup_file}", logger)

            if len(kept_files) != len(self.backup_index["deleted_files"]):
                self.backup_index["deleted_files"] = kept_files
                self._save_backup_index()
                log_success(
                    f"Cleaned up {len(self.backup_index['deleted_files']) - len(kept_files)} expired deleted file backups", logger)

        except Exception as e:
            log_error(e, "Failed to cleanup expired deleted files", logger)

    def cleanup_old_backups(self, max_age_days: int = 30):
        """Clean up backups older than specified days."""
        try:
            cutoff_date = datetime.now().timestamp() - (max_age_days * 24 * 60 * 60)

            for file_path, backups in self.backup_index["files"].items():

                recent_backups = []
                for backup in backups:
                    backup_time = datetime.fromisoformat(
                        backup["timestamp"]).timestamp()
                    if backup_time > cutoff_date:
                        recent_backups.append(backup)
                    else:

                        backup_path = self._get_backup_path(
                            file_path, backup["version"])
                        try:
                            backup_path.unlink(missing_ok=True)
                        except Exception:
                            pass

                if recent_backups:
                    self.backup_index["files"][file_path] = recent_backups
                else:
                    del self.backup_index["files"][file_path]

            self._save_backup_index()
            log_success("Old backups cleaned up", logger)

        except Exception as e:
            log_error(e, "Failed to cleanup old backups", logger)


def log_error(error, message, logger):
    """Log error messages."""
    try:
        logger.error(f"{message}: {str(error)}")
    except:
        pass


def log_success(message, logger):
    """Log success messages."""
    try:
        logger.info(message)
    except:
        pass
