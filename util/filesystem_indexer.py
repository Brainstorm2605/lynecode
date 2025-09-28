import os
import json
from pathlib import Path
from typing import Dict, List, Optional, Set
from datetime import datetime
import ctypes
import difflib

from util.logging import get_logger, log_function_call, log_error, log_success, log_info

logger = get_logger("filesystem_indexer")


class FileSystemIndexer:
    """Manages filesystem indexing for Lyne projects."""

    def __init__(self, project_path: str):
        """Initialize the filesystem indexer.

        Args:
            project_path: The user's working directory to index
        """
        self.project_path = Path(project_path).resolve()
        self.index_dir = self.project_path / "lynecode"
        self.index_file = self.index_dir / "index.json"

        self.exclude_patterns = {
            "directories": {
                "__pycache__", "venv", "env", ".env", "node_modules",
                ".git", ".vscode", ".idea", "dist", "build",
                "target", "bin", "obj", ".next", ".nuxt", "lynecode", "time_machine"
            },
            "files": {"*.pyc", "*.pyo", "*.pyd", "*.log", "debug.log"},
            "extensions": {".pyc", ".pyo", ".pyd", ".log"}
        }

        self.index_data = {
            "project_path": str(self.project_path),
            "created_at": datetime.now().isoformat(),
            "files": [],
            "folders": []
        }

        self._ensure_hidden_directory()

    def _ensure_hidden_directory(self):
        """Ensure the hidden lynecode directory exists."""
        try:
            self.index_dir.mkdir(parents=True, exist_ok=True)
            self._make_hidden(str(self.index_dir))
        except Exception as e:
            log_error(e, "Failed to create hidden index directory", logger)

    def _make_hidden(self, path: str):
        """Make the index directory hidden across platforms.

        Windows: Set Hidden | System | Not Content Indexed attributes
        macOS:   Use chflags hidden
        Linux:   Best-effort: chmod 700 and add entry to parent .hidden file
        """
        try:
            import sys
            p = Path(path)

            if os.name == 'nt':
                try:
                    FILE_ATTRIBUTE_HIDDEN = 0x02
                    FILE_ATTRIBUTE_SYSTEM = 0x04
                    FILE_ATTRIBUTE_NOT_CONTENT_INDEXED = 0x2000
                    attrs = FILE_ATTRIBUTE_HIDDEN | FILE_ATTRIBUTE_SYSTEM | FILE_ATTRIBUTE_NOT_CONTENT_INDEXED
                    ctypes.windll.kernel32.SetFileAttributesW(str(p), attrs)
                except Exception:
                    pass
                return

            if sys.platform == 'darwin':
                try:
                    import subprocess
                    subprocess.run(['chflags', 'hidden', str(
                        p)], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except Exception:
                    pass
                return

            try:
                os.chmod(str(p), 0o700)
            except Exception:
                pass

            try:
                hidden_file = p.parent / '.hidden'
                entry = p.name
                existing = ""
                if hidden_file.exists():
                    try:
                        existing = hidden_file.read_text(
                            encoding='utf-8', errors='ignore')
                    except Exception:
                        existing = ""
                if entry not in existing.splitlines():
                    with open(hidden_file, 'a', encoding='utf-8') as hf:
                        hf.write(entry + "\n")
            except Exception:
                pass
        except Exception as e:
            pass

    def _should_exclude_directory(self, dir_path: str) -> bool:
        """Check if directory should be excluded from indexing."""
        dir_name = os.path.basename(dir_path)

        if dir_name.startswith('.'):
            return True

        if dir_name in self.exclude_patterns["directories"]:
            return True

        parts = Path(dir_path).parts
        for part in parts:
            if part in self.exclude_patterns["directories"]:
                return True

        return False

    def _should_exclude_file(self, file_path: str) -> bool:
        """Check if file should be excluded from indexing."""
        file_name = os.path.basename(file_path)

        if file_name.startswith('.'):
            return True

        if file_name in self.exclude_patterns["files"]:
            return True

        _, ext = os.path.splitext(file_name)
        if ext in self.exclude_patterns["extensions"]:
            return True

        return False

    def _scan_directory(self, dir_path: str) -> Dict:
        """Scan a directory and return its structure."""
        try:
            items = os.listdir(dir_path)
            structure = {"files": [], "folders": []}

            for item in items:
                item_path = os.path.join(dir_path, item)
                full_path = os.path.abspath(item_path)

                if os.path.isfile(item_path):
                    if not self._should_exclude_file(item_path):
                        file_info = {
                            "name": item,
                            "path": full_path,
                            "type": "file"
                        }
                        structure["files"].append(file_info)

                elif os.path.isdir(item_path):
                    if not self._should_exclude_directory(item_path):
                        folder_info = {
                            "name": item,
                            "path": full_path,
                            "type": "folder"
                        }
                        structure["folders"].append(folder_info)

            return structure

        except PermissionError:
            return {"files": [], "folders": []}
        except Exception as e:
            log_error(e, f"Error scanning directory: {dir_path}", logger)
            return {"files": [], "folders": []}

    def build_index(self):
        """Build the complete filesystem index."""
        log_info("Starting filesystem index build", logger)

        files = []
        folders = []

        def walk_directory(path: str):
            """Recursively walk directory tree."""
            structure = self._scan_directory(path)

            for folder in structure["folders"]:
                walk_directory(folder["path"])

            for file_info in structure["files"]:
                files.append(file_info)

            for folder_info in structure["folders"]:
                folders.append(folder_info)

        walk_directory(str(self.project_path))

        self.index_data["files"] = files
        self.index_data["folders"] = folders

        self._save_index()
        log_success(
            f"Index built: {len(files)} files, {len(folders)} folders", logger)

    def _save_index(self):
        """Save the index to the hidden directory."""
        try:
            with open(self.index_file, 'w', encoding='utf-8') as f:
                json.dump(self.index_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            log_error(e, "Failed to save index file", logger)

    def find_files(self, name_pattern: str = None, path_pattern: str = None) -> List[Dict]:
        """Search for files in the index."""
        results = []

        for file_info in self.index_data["files"]:
            if name_pattern and name_pattern.lower() not in file_info["name"].lower():
                continue
            if path_pattern and path_pattern.lower() not in file_info["path"].lower():
                continue
            results.append(file_info)

        return results

    def find_folders(self, name_pattern: str = None, path_pattern: str = None) -> List[Dict]:
        """Search for folders in the index."""
        results = []

        for folder_info in self.index_data["folders"]:
            if name_pattern and name_pattern.lower() not in folder_info["name"].lower():
                continue
            if path_pattern and path_pattern.lower() not in folder_info["path"].lower():
                continue
            results.append(folder_info)

        return results

    def get_index_stats(self) -> Dict:
        """Get statistics about the current index."""
        return {
            "project_path": self.index_data["project_path"],
            "created_at": self.index_data["created_at"],
            "file_count": len(self.index_data["files"]),
            "folder_count": len(self.index_data["folders"]),
            "index_path": str(self.index_file)
        }

    def load_index(self) -> bool:
        try:
            if self.index_file.exists():
                with open(self.index_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, dict) and "files" in data and "folders" in data:
                        self.index_data = data
                        try:
                            updated_files = []
                            for fi in self.index_data.get("files", []):
                                p = fi.get("path", "")
                                if p and os.path.isfile(p):
                                    updated_files.append(fi)
                            updated_folders = []
                            for fo in self.index_data.get("folders", []):
                                p = fo.get("path", "")
                                if p and os.path.isdir(p):
                                    updated_folders.append(fo)
                            if len(updated_files) != len(self.index_data.get("files", [])) or len(updated_folders) != len(self.index_data.get("folders", [])):
                                self.index_data["files"] = updated_files
                                self.index_data["folders"] = updated_folders
                                self._save_index()
                        except Exception:
                            pass
                        return True
            return False
        except Exception as e:
            log_error(e, "Failed to load index file", logger)
            return False

    def fuzzy_find_files(self, term: str, limit: int = 5) -> List[Dict]:
        term_l = term.lower()
        candidates = []
        names = [f.get("name", "") for f in self.index_data.get("files", [])]
        name_to_items = {}
        for f in self.index_data.get("files", []):
            name_to_items.setdefault(f.get("name", ""), []).append(f)
        scores = {}
        for name in names:
            nl = name.lower()
            score = 0.0
            if term_l in nl:
                score = 1.0 - (nl.find(term_l) / max(1, len(nl)))
                score += 0.5
            else:
                score = difflib.SequenceMatcher(a=term_l, b=nl).ratio()
            scores[name] = max(scores.get(name, 0.0), score)
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        for name, _ in ranked[: max(50, limit * 5)]:
            for item in name_to_items.get(name, []):
                candidates.append(item)
        seen = set()
        unique = []
        for item in candidates:
            key = item.get("path")
            if key not in seen:
                seen.add(key)
                unique.append(item)
            if len(unique) >= limit:
                break
        return unique

    def fuzzy_find_folders(self, term: str, limit: int = 5) -> List[Dict]:
        term_l = term.lower()
        candidates = []
        names = [f.get("name", "") for f in self.index_data.get("folders", [])]
        name_to_items = {}
        for f in self.index_data.get("folders", []):
            name_to_items.setdefault(f.get("name", ""), []).append(f)
        scores = {}
        for name in names:
            nl = name.lower()
            score = 0.0
            if term_l in nl:
                score = 1.0 - (nl.find(term_l) / max(1, len(nl)))
                score += 0.5
            else:
                score = difflib.SequenceMatcher(a=term_l, b=nl).ratio()
            scores[name] = max(scores.get(name, 0.0), score)
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        for name, _ in ranked[: max(50, limit * 5)]:
            for item in name_to_items.get(name, []):
                candidates.append(item)
        seen = set()
        unique = []
        for item in candidates:
            key = item.get("path")
            if key not in seen:
                seen.add(key)
                unique.append(item)
            if len(unique) >= limit:
                break
        return unique
