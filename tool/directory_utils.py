#!/usr/bin/env python3
"""
Directory understanding and file system utility tools.
Provides various functions for checking file/folder existence, exploring structure, and analyzing paths.
"""

import os
import glob
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from util.logging import get_logger, log_function_call, log_error, log_success, log_info, log_warning

logger = get_logger("directory_utils")

EXCLUDED_DIRS = {
    'venv', 'ven', '__pycache__', 'node_modules', '.git', '.svn', '.hg',
    'build', 'dist', 'target', '.next', '.nuxt', 'vendor', 'packages',
    'bin', 'obj', '.vs', '.vscode', '.idea',
    '.pytest_cache', '.mypy_cache', '.tox', '.coverage', 'htmlcov',
    'env', 'ENV', 'venv', 'VENV', '.env', 'site-packages', 'lib',
    'Lib', 'library', 'libraries', 'deps', 'dependencies', 'lynecode', 'time_machine'
}

EXCLUDED_FILE_PATTERNS = [
    '**/*.pyc',
    '**/*.pyo',
    '**/*.bin',
    '**/*.exe',
    '**/*.dll',
    '**/*.so',
    '**/*.dylib',
    '**/*.class',
    '**/*.jar',
    '**/*.war',
    '**/*.zip',
    '**/*.tar',
    '**/*.gz',
    '**/*.bz2',
    '**/*.rar',
    '**/*.7z',
    '**/*.doc',
    '**/*.docx',
    '**/*.xls',
    '**/*.xlsx',
    '**/*.ppt',
    '**/*.pptx',
    '**/*.odt',
    '**/*.ods',
    '**/*.odp',
    '**/*.DS_Store',
]


def file_exists(file_path: str) -> Dict:
    """
    Check if a file exists at the specified path.

    Args:
        file_path: Path to the file to check

    Returns:
        Descriptive string about file existence status
    """
    try:
        log_function_call("file_exists", {"file_path": file_path}, logger)

        normalized_path = os.path.normpath(file_path)

        if os.path.exists(file_path):
            if os.path.isfile(file_path):

                size = os.path.getsize(file_path)
                size_str = f"{size} bytes"
                if size > 1024:
                    size_str = f"{size/1024:.1f} KB"
                if size > 1024*1024:
                    size_str = f"{size/(1024*1024):.1f} MB"

                is_readable = os.access(file_path, os.R_OK)
                is_writable = os.access(file_path, os.W_OK)
                access = []
                if is_readable:
                    access.append("readable")
                if is_writable:
                    access.append("writable")
                access_str = " and ".join(access)

                log_success(f"File exists: {normalized_path}", logger)
                return {
                    "success": True,
                    "tool_name": "file_exists",
                    "result": {
                        "status": "exists",
                        "message": f"File exists: '{normalized_path}' ({size_str}, {access_str})",
                        "file_path": file_path,
                        "normalized_path": normalized_path,
                        "size": size,
                        "size_str": size_str,
                        "readable": is_readable,
                        "writable": is_writable
                    }
                }
            else:
                log_success(
                    f"Path exists but is not a file: {normalized_path}", logger)
                return {
                    "success": True,
                    "tool_name": "file_exists",
                    "result": {
                        "status": "path_exists_not_file",
                        "message": f"Path exists but is not a file: '{normalized_path}'",
                        "file_path": file_path,
                        "normalized_path": normalized_path
                    }
                }
        else:
            log_success(f"File does not exist: {normalized_path}", logger)

            parent_dir = os.path.dirname(file_path)
            if os.path.exists(parent_dir):
                return {
                    "success": True,
                    "tool_name": "file_exists",
                    "result": {
                        "status": "not_found_parent_exists",
                        "message": f"File does not exist: '{normalized_path}'. Parent directory exists.",
                        "file_path": file_path,
                        "normalized_path": normalized_path,
                        "parent_exists": True
                    }
                }
            else:
                return {
                    "success": True,
                    "tool_name": "file_exists",
                    "result": {
                        "status": "not_found_parent_missing",
                        "message": f"File does not exist: '{normalized_path}'. Parent directory does not exist.",
                        "file_path": file_path,
                        "normalized_path": normalized_path,
                        "parent_exists": False
                    }
                }
    except Exception as e:
        log_error(e, f"Error checking file existence: {file_path}", logger)
        return {
            "success": False,
            "tool_name": "file_exists",
            "result": {
                "status": "error",
                "message": f"Error checking file existence: '{normalized_path}'. {str(e)}",
                "file_path": file_path,
                "normalized_path": normalized_path,
                "error": str(e)
            }
        }


def folder_exists(folder_path: str) -> Dict:
    """
    Check if a folder exists at the specified path.

    Args:
        folder_path: Path to the folder to check

    Returns:
        Descriptive string about folder existence status
    """
    try:
        log_function_call("folder_exists", {
                          "folder_path": folder_path}, logger)

        normalized_path = os.path.normpath(folder_path)

        if os.path.exists(folder_path):
            if os.path.isdir(folder_path):

                is_readable = os.access(folder_path, os.R_OK)
                is_writable = os.access(folder_path, os.W_OK)
                is_executable = os.access(folder_path, os.X_OK)

                access = []
                if is_readable:
                    access.append("readable")
                if is_writable:
                    access.append("writable")
                if is_executable:
                    access.append("executable")
                access_str = ", ".join(access)

                try:
                    with os.scandir(folder_path) as entries:
                        item_count = sum(1 for _ in entries)
                    item_str = f"contains {item_count} items"
                except:
                    item_str = "contents could not be read"

                log_success(f"Folder exists: {normalized_path}", logger)
                return {
                    "success": True,
                    "tool_name": "folder_exists",
                    "result": {
                        "status": "exists",
                        "message": f"Directory exists: '{normalized_path}' ({item_str}, {access_str})",
                        "folder_path": folder_path,
                        "normalized_path": normalized_path,
                        "item_count": item_count if isinstance(item_count, int) else None,
                        "readable": is_readable,
                        "writable": is_writable,
                        "executable": is_executable
                    }
                }
            else:
                log_success(
                    f"Path exists but is not a directory: {normalized_path}", logger)
                return {
                    "success": True,
                    "tool_name": "folder_exists",
                    "result": {
                        "status": "path_exists_not_directory",
                        "message": f"Path exists but is not a directory: '{normalized_path}'",
                        "folder_path": folder_path,
                        "normalized_path": normalized_path
                    }
                }
        else:
            log_success(f"Directory does not exist: {normalized_path}", logger)

            parent_dir = os.path.dirname(folder_path)
            if parent_dir and os.path.exists(parent_dir):
                is_writable = os.access(parent_dir, os.W_OK)
                if is_writable:
                    return {
                        "success": True,
                        "tool_name": "folder_exists",
                        "result": {
                            "status": "not_found_parent_writable",
                            "message": f"Directory does not exist: '{normalized_path}'. Parent directory exists and is writable.",
                            "folder_path": folder_path,
                            "normalized_path": normalized_path,
                            "parent_exists": True,
                            "parent_writable": True
                        }
                    }
                else:
                    return {
                        "success": True,
                        "tool_name": "folder_exists",
                        "result": {
                            "status": "not_found_parent_readonly",
                            "message": f"Directory does not exist: '{normalized_path}'. Parent directory exists but is not writable.",
                            "folder_path": folder_path,
                            "normalized_path": normalized_path,
                            "parent_exists": True,
                            "parent_writable": False
                        }
                    }
            else:
                return {
                    "success": True,
                    "tool_name": "folder_exists",
                    "result": {
                        "status": "not_found_no_parent",
                        "message": f"Directory does not exist: '{normalized_path}'. Parent directory does not exist.",
                        "folder_path": folder_path,
                        "normalized_path": normalized_path,
                        "parent_exists": False
                    }
                }
    except Exception as e:
        log_error(e, f"Error checking folder existence: {folder_path}", logger)
        return {
            "success": False,
            "tool_name": "folder_exists",
            "result": {
                "status": "error",
                "message": f"Error checking directory existence: '{normalized_path}'. {str(e)}",
                "folder_path": folder_path,
                "normalized_path": normalized_path,
                "error": str(e)
            }
        }


def get_folder_structure(folder_path: str, max_depth: int = 3, include_files: bool = True,
                         include_hidden: bool = False) -> Dict:
    """
    Get the structure of a folder including subfolders and files.

    Args:
        folder_path: Path to the folder to analyze
        max_depth: Maximum depth to explore (default: 3)
        include_files: Whether to include files in the structure (default: True)
        include_hidden: Whether to include hidden files/folders (default: False)

    Returns:
        Dictionary containing clean folder structure
    """
    try:
        log_function_call("get_folder_structure", {
            "folder_path": folder_path,
            "max_depth": max_depth,
            "include_files": include_files,
            "include_hidden": include_hidden
        }, logger)

        folder_status = folder_exists(folder_path)
        if "does not exist" in folder_status:
            log_error(
                Exception(f"Folder does not exist: {folder_path}"), "Folder not found", logger)
            return {}

        def explore_folder(path: str, depth: int = 0) -> Dict:
            if depth > max_depth:
                return {}

            try:
                entries = list(os.scandir(path))
                if not include_hidden:
                    entries = [
                        entry for entry in entries if not entry.name.startswith('.')]

                def should_exclude_path(path: str) -> bool:
                    """Check if path should be excluded."""
                    import os
                    dir_name = os.path.basename(path)
                    return dir_name in EXCLUDED_DIRS

                entries = [
                    entry for entry in entries
                    if not (entry.is_dir() and should_exclude_path(entry.path))
                ]

                structure = {
                    "folders": [],
                    "files": []
                }

                for entry in sorted(entries, key=lambda e: e.name):
                    if entry.is_dir():
                        sub_structure = explore_folder(entry.path, depth + 1)
                        if sub_structure:
                            structure["folders"].append({
                                "name": entry.name,
                                "path": entry.path,
                                "contents": sub_structure
                            })
                        else:
                            structure["folders"].append({
                                "name": entry.name,
                                "path": entry.path
                            })
                    elif include_files and entry.is_file():
                        structure["files"].append({
                            "name": entry.name,
                            "path": entry.path
                        })

                return structure

            except PermissionError:
                return {}
            except Exception as e:
                return {}

        result = explore_folder(folder_path)

        if result and isinstance(result, dict):
            folders_empty = not result.get("folders", [])
            files_empty = not result.get("files", [])

            if folders_empty and files_empty:
                empty_message = f"FOLDER STATUS: The folder '{folder_path}' exists but is completely empty (no files, no subfolders). This is likely a fresh/empty directory, no need to call get_folder_structure again on this path unless content is added later."
                log_success(f"Empty folder detected: {folder_path}", logger)
                return empty_message

        log_success(f"Folder structure retrieved for: {folder_path}", logger)
        return result

    except Exception as e:
        log_error(e, f"Error getting folder structure: {folder_path}", logger)
        return {}


def get_file_info(file_path: str) -> Optional[Dict]:
    """
    Get essential information about a file.

    Args:
        file_path: Path to the file

    Returns:
        Dictionary with essential file information or None if error
    """
    try:
        log_function_call("get_file_info", {"file_path": file_path}, logger)

        file_status = file_exists(file_path)
        if file_status.get("status") != "exists":
            log_error(
                Exception(f"File does not exist: {file_path}"), "File not found", logger)
            return {
                "success": False,
                "tool_name": "get_file_info",
                "result": {
                    "status": "file_not_found",
                    "message": f"File does not exist: '{file_path}'",
                    "file_path": file_path
                }
            }

        stat_info = os.stat(file_path)
        file_info = {
            "status": "success",
            "message": f"SUCCESS: Retrieved file information for '{file_path}'.",
            "file_path": file_path,
            "name": os.path.basename(file_path),
            "path": file_path,
            "size": stat_info.st_size,
            "extension": os.path.splitext(file_path)[1],
            "readonly": not os.access(file_path, os.W_OK)
        }

        log_success(f"File info retrieved for: {file_path}", logger)
        return {
            "success": True,
            "tool_name": "get_file_info",
            "result": file_info
        }

    except Exception as e:
        log_error(e, f"Error getting file info: {file_path}", logger)
        return {
            "success": False,
            "tool_name": "get_file_info",
            "result": {
                "status": "error",
                "message": f"Error getting file info: '{file_path}'. {str(e)}",
                "file_path": file_path,
                "error": str(e)
            }
        }


def find_files_by_pattern(pattern: str, root_path: str, recursive: bool = True,
                          max_results: int = 100) -> List[str]:
    """
    Find files matching a glob pattern.

    Args:
        pattern: Glob pattern to search for (e.g., "*.py", "*.{txt,md}")
        root_path: Root directory to search in (required)
        recursive: Whether to search recursively (default: True)
        max_results: Maximum number of results to return (default: 100)

    Returns:
        List of file paths matching the pattern
    """
    try:
        log_function_call("find_files_by_pattern", {
            "pattern": pattern,
            "root_path": root_path,
            "recursive": recursive,
            "max_results": max_results
        }, logger)

        if not folder_exists(root_path):
            error_message = f"PATH NOT FOUND: Root path '{root_path}' does not exist or is not accessible."
            log_error(Exception(error_message), "Root path not found", logger)
            return {
                "success": False,
                "tool_name": "find_files_by_pattern",
                "result": {
                    "status": "path_not_found",
                    "message": error_message,
                    "files": [],
                    "pattern": pattern,
                    "root_path": root_path,
                    "recursive": recursive,
                    "max_results": max_results,
                    "found_count": 0
                }
            }

        log_info(
            f"Searching for pattern: {pattern} in {root_path} (recursive: {recursive})", logger)

        import threading
        import re
        import fnmatch

        matching_files = []
        search_error = None

        def expand_braces(pattern: str) -> list:
            """Robust brace expansion for patterns like *.{js,py}, **/{a,b}/**, etc."""
            try:

                if '{' not in pattern or '}' not in pattern:
                    return [pattern]

                open_count = pattern.count('{')
                close_count = pattern.count('}')
                if open_count != close_count or open_count == 0:
                    return [pattern]

                brace_groups = []
                i = 0
                while i < len(pattern):
                    if pattern[i] == '{':

                        brace_start = i
                        brace_level = 1
                        j = i + 1
                        while j < len(pattern) and brace_level > 0:
                            if pattern[j] == '{':
                                brace_level += 1
                            elif pattern[j] == '}':
                                brace_level -= 1
                            j += 1

                        if brace_level == 0:
                            brace_content = pattern[brace_start + 1:j - 1]
                            if brace_content:
                                options = [opt.strip() for opt in brace_content.split(
                                    ',') if opt.strip()]
                                if options:
                                    brace_groups.append({
                                        'start': brace_start,
                                        'end': j,
                                        'options': options
                                    })
                        i = j
                    else:
                        i += 1

                if not brace_groups:
                    return [pattern]

                def generate_combinations(groups, index=0, current_parts=None):
                    if current_parts is None:
                        current_parts = [pattern[:groups[0]['start']]]

                    if index >= len(groups):

                        if index == len(groups):
                            suffix_start = groups[-1]['end']
                            if suffix_start < len(pattern):
                                current_parts.append(pattern[suffix_start:])
                        return [''.join(current_parts)]

                    group = groups[index]
                    results = []

                    for option in group['options']:
                        new_parts = current_parts.copy()

                        new_parts.append(option)

                        next_start = groups[index + 1]['start'] if index + \
                            1 < len(groups) else len(pattern)
                        between_text = pattern[group['end']:next_start]
                        if between_text:
                            new_parts.append(between_text)

                        results.extend(generate_combinations(
                            groups, index + 1, new_parts))

                    return results

                total_expansions = 1
                for group in brace_groups:
                    total_expansions *= len(group['options'])

                if total_expansions > 1000:
                    log_warning(
                        f"Brace expansion too large ({total_expansions} patterns) for '{pattern}', using original pattern", logger)
                    return [pattern]

                expanded_patterns = generate_combinations(brace_groups)

                expanded_patterns = list(
                    set(p for p in expanded_patterns if p.strip()))

                return expanded_patterns if expanded_patterns else [pattern]

            except Exception as e:

                log_warning(
                    f"Brace expansion failed for pattern '{pattern}': {str(e)}", logger)

                return [pattern]

        extension_filter = None
        if pattern.startswith("*.") and len(pattern) > 2:

            if '{' in pattern and '}' in pattern:

                expanded_exts = []
                expanded_patterns = expand_braces(pattern)
                for exp_pat in expanded_patterns:
                    if exp_pat.startswith("*.") and len(exp_pat) > 2:
                        ext = exp_pat[1:]
                        if ext not in expanded_exts:
                            expanded_exts.append(ext)
                if expanded_exts:
                    extension_filter = tuple(expanded_exts)
            else:

                extension_filter = pattern[1:]

        compiled_search_pattern = re.compile(fnmatch.translate(pattern))
        compiled_file_patterns = [re.compile(
            fnmatch.translate(pat)) for pat in EXCLUDED_FILE_PATTERNS]

        def should_exclude_path(path: str) -> bool:
            """Check if path should be excluded."""
            import os
            dir_name = os.path.basename(path)
            return dir_name in EXCLUDED_DIRS

        def should_exclude_file(file_path: str) -> bool:
            """Check if file should be excluded based on file patterns."""
            for i, pattern in enumerate(EXCLUDED_FILE_PATTERNS):
                try:
                    if compiled_file_patterns[i].search(file_path):
                        return True
                except:
                    if pattern in file_path:
                        return True
            return False

        def search_directory(search_path: str):
            """Recursively search directory with excludes."""
            nonlocal matching_files, max_results

            if len(matching_files) >= max_results:
                return

            try:
                for entry in os.scandir(search_path):
                    if len(matching_files) >= max_results:
                        break

                    if entry.is_file():
                        if extension_filter:
                            if isinstance(extension_filter, tuple):

                                if not any(entry.name.endswith(ext) for ext in extension_filter):
                                    continue
                            else:

                                if not entry.name.endswith(extension_filter):
                                    continue

                        try:
                            if compiled_search_pattern.match(entry.name):
                                if not should_exclude_path(entry.path) and not should_exclude_file(entry.path):
                                    matching_files.append(entry.path)
                                    continue
                        except:
                            pass

                        try:

                            if '{' in pattern and '}' in pattern:
                                expanded_patterns = expand_braces(pattern)
                                for expanded_pattern in expanded_patterns:
                                    try:

                                        if '**' in expanded_pattern:

                                            if glob.fnmatch.fnmatch(entry.path, expanded_pattern):
                                                if not should_exclude_path(entry.path) and not should_exclude_file(entry.path):
                                                    matching_files.append(
                                                        entry.path)
                                                    break
                                        else:

                                            if glob.fnmatch.fnmatch(entry.name, expanded_pattern):
                                                if not should_exclude_path(entry.path) and not should_exclude_file(entry.path):
                                                    matching_files.append(
                                                        entry.path)
                                                    break
                                    except:
                                        pass
                            else:

                                if '**' in pattern:

                                    if glob.fnmatch.fnmatch(entry.path, pattern):
                                        if not should_exclude_path(entry.path) and not should_exclude_file(entry.path):
                                            matching_files.append(entry.path)
                                else:

                                    if glob.fnmatch.fnmatch(entry.name, pattern):
                                        if not should_exclude_path(entry.path) and not should_exclude_file(entry.path):
                                            matching_files.append(entry.path)
                        except:

                            if pattern in entry.name:
                                if not should_exclude_path(entry.path) and not should_exclude_file(entry.path):
                                    matching_files.append(entry.path)
                    elif entry.is_dir() and recursive:

                        if not should_exclude_path(entry.path):
                            search_directory(entry.path)
            except PermissionError:
                pass
            except Exception as e:
                log_error(
                    e, f"Error searching directory: {search_path}", logger)

        def run_search():
            nonlocal matching_files, search_error
            try:
                if recursive:
                    search_directory(root_path)
                else:

                    for entry in os.scandir(root_path):
                        if entry.is_file():
                            if extension_filter:
                                if isinstance(extension_filter, tuple):

                                    if not any(entry.name.endswith(ext) for ext in extension_filter):
                                        continue
                                else:

                                    if not entry.name.endswith(extension_filter):
                                        continue

                            try:
                                if compiled_search_pattern.match(entry.name):
                                    if not should_exclude_path(entry.path) and not should_exclude_file(entry.path):
                                        matching_files.append(entry.path)
                                        if len(matching_files) >= max_results:
                                            break
                                        continue
                            except:
                                pass

                            try:

                                if '{' in pattern and '}' in pattern:
                                    expanded_patterns = expand_braces(pattern)
                                    for expanded_pattern in expanded_patterns:
                                        try:

                                            if '**' in expanded_pattern:

                                                if glob.fnmatch.fnmatch(entry.path, expanded_pattern):
                                                    if not should_exclude_path(entry.path) and not should_exclude_file(entry.path):
                                                        matching_files.append(
                                                            entry.path)
                                                        if len(matching_files) >= max_results:
                                                            break
                                                        break
                                            else:

                                                if glob.fnmatch.fnmatch(entry.name, expanded_pattern):
                                                    if not should_exclude_path(entry.path) and not should_exclude_file(entry.path):
                                                        matching_files.append(
                                                            entry.path)
                                                        if len(matching_files) >= max_results:
                                                            break
                                                        break
                                        except:
                                            pass
                                else:

                                    if '**' in pattern:

                                        if glob.fnmatch.fnmatch(entry.path, pattern):
                                            if not should_exclude_path(entry.path) and not should_exclude_file(entry.path):
                                                matching_files.append(
                                                    entry.path)
                                                if len(matching_files) >= max_results:
                                                    break
                                    else:

                                        if glob.fnmatch.fnmatch(entry.name, pattern):
                                            if not should_exclude_path(entry.path) and not should_exclude_file(entry.path):
                                                matching_files.append(
                                                    entry.path)
                                                if len(matching_files) >= max_results:
                                                    break
                            except:

                                if pattern in entry.name:
                                    if not should_exclude_path(entry.path) and not should_exclude_file(entry.path):
                                        matching_files.append(entry.path)
                                        if len(matching_files) >= max_results:
                                            break
            except Exception as e:
                search_error = e

        search_thread = threading.Thread(target=run_search)
        search_thread.daemon = True
        search_thread.start()

        search_thread.join(timeout=160)

        if search_thread.is_alive():
            partial_results = matching_files[:max_results]
            timeout_message = f"SEARCH TIMEOUT: Pattern '{pattern}' search timed out. Found {len(partial_results)} files so far."
            log_warning(timeout_message, logger)
            return {
                "success": True,
                "tool_name": "find_files_by_pattern",
                "result": {
                    "status": "timeout",
                    "message": timeout_message,
                    "files": partial_results,
                    "pattern": pattern,
                    "root_path": root_path,
                    "recursive": recursive,
                    "max_results": max_results,
                    "found_count": len(partial_results)
                }
            }

        if search_error:
            error_message = f"SEARCH ERROR: Failed to search for pattern '{pattern}'. Error: {str(search_error)}."
            log_error(search_error, error_message, logger)
            return {
                "success": False,
                "tool_name": "find_files_by_pattern",
                "result": {
                    "status": "error",
                    "message": error_message,
                    "files": [],
                    "pattern": pattern,
                    "root_path": root_path,
                    "recursive": recursive,
                    "max_results": max_results,
                    "found_count": 0
                }
            }

        result = matching_files[:max_results]

        if len(result) == 0:
            no_results_message = f"NO FILES FOUND: Pattern '{pattern}' matched 0 files in '{root_path}'."
            log_success(no_results_message, logger)
            return {
                "success": True,
                "tool_name": "find_files_by_pattern",
                "result": {
                    "status": "no_results",
                    "message": no_results_message,
                    "files": [],
                    "pattern": pattern,
                    "root_path": root_path,
                    "recursive": recursive,
                    "max_results": max_results,
                    "found_count": 0
                }
            }

        success_message = f"SUCCESS: Found {len(result)} files matching pattern '{pattern}'."
        log_success(success_message, logger)
        return {
            "success": True,
            "tool_name": "find_files_by_pattern",
            "result": {
                "status": "success",
                "message": success_message,
                "files": result,
                "pattern": pattern,
                "root_path": root_path,
                "recursive": recursive,
                "max_results": max_results,
                "found_count": len(result)
            }
        }

    except Exception as e:
        exception_message = f"UNEXPECTED ERROR: Failed while searching for pattern '{pattern}'. Error: {str(e)}."
        log_error(e, exception_message, logger)
        return {
            "success": False,
            "tool_name": "find_files_by_pattern",
            "result": {
                "status": "critical_error",
                "message": exception_message,
                "files": [],
                "pattern": pattern,
                "root_path": root_path,
                "recursive": recursive,
                "max_results": max_results,
                "found_count": 0
            }
        }


def get_path_type(path: str) -> Dict:
    """
    Determine the type of a path (file, folder, or doesn't exist).

    Args:
        path: Path to check

    Returns:
        "file", "folder", or "not_found"
    """
    try:
        log_function_call("get_path_type", {"path": path}, logger)

        if os.path.isfile(path):
            result = {
                "status": "success",
                "message": f"Path is a file: '{path}'",
                "path": path,
                "type": "file",
                "exists": True
            }
        elif os.path.isdir(path):
            result = {
                "status": "success",
                "message": f"Path is a directory: '{path}'",
                "path": path,
                "type": "folder",
                "exists": True
            }
        else:
            result = {
                "status": "not_found",
                "message": f"Path does not exist: '{path}'",
                "path": path,
                "type": "not_found",
                "exists": False
            }

        log_success(f"Path type determined: {result['type']}", logger)
        return {
            "success": True,
            "tool_name": "get_path_type",
            "result": result
        }

    except Exception as e:
        log_error(e, f"Error determining path type: {path}", logger)
        return {
            "success": False,
            "tool_name": "get_path_type",
            "result": {
                "status": "error",
                "message": f"Error determining path type: '{path}'. {str(e)}",
                "path": path,
                "type": "error",
                "exists": None,
                "error": str(e)
            }
        }


def get_common_paths(root_path: str, max_depth: int = 2) -> Dict:
    """
    Get common paths for quick navigation - just files and folders.

    Args:
        root_path: Root directory to analyze (required)
        max_depth: Maximum depth to explore (default: 2)

    Returns:
        Dictionary with just files and folders
    """
    try:
        log_function_call("get_common_paths", {
            "root_path": root_path,
            "max_depth": max_depth
        }, logger)

        folder_status = folder_exists(root_path)
        if folder_status.get("status") != "exists":
            log_error(Exception(
                f"Root path does not exist: {root_path}"), "Root path not found", logger)
            return {
                "success": False,
                "tool_name": "get_common_paths",
                "result": {
                    "status": "path_not_found",
                    "message": f"Root path does not exist: '{root_path}'",
                    "root_path": root_path,
                    "max_depth": max_depth,
                    "files": [],
                    "folders": [],
                    "total_files": 0,
                    "total_folders": 0
                }
            }

        common_paths = {
            "files": [],
            "folders": []
        }

        def scan_directory(path: str, depth: int = 0):
            if depth > max_depth:
                return

            try:
                def should_exclude_path_common(path: str) -> bool:
                    """Check if path should be excluded."""
                    import os
                    dir_name = os.path.basename(path)
                    return dir_name in EXCLUDED_DIRS

                for entry in os.scandir(path):
                    if entry.is_file():
                        common_paths["files"].append(entry.path)
                    elif entry.is_dir() and depth < max_depth and not should_exclude_path_common(entry.path):
                        common_paths["folders"].append(entry.path)
                        scan_directory(entry.path, depth + 1)

            except PermissionError:
                pass
            except Exception as e:
                log_error(e, f"Error scanning directory: {path}", logger)

        scan_directory(root_path)

        common_paths["files"] = common_paths["files"][:1000]
        common_paths["folders"] = common_paths["folders"][:500]

        file_count = len(common_paths["files"])
        folder_count = len(common_paths["folders"])

        result = {
            "status": "success",
            "message": f"SUCCESS: Retrieved common paths for '{root_path}' (max_depth={max_depth}). Found {folder_count} folders and {file_count} files.",
            "root_path": root_path,
            "max_depth": max_depth,
            "files": common_paths["files"],
            "folders": common_paths["folders"],
            "total_files": file_count,
            "total_folders": folder_count,
            "files_limit": 1000,
            "folders_limit": 500
        }

        log_success(f"Common paths retrieved for: {root_path}", logger)
        return {
            "success": True,
            "tool_name": "get_common_paths",
            "result": result
        }

    except Exception as e:
        log_error(e, f"Error getting common paths: {root_path}", logger)
        return {
            "success": False,
            "tool_name": "get_common_paths",
            "result": {
                "status": "error",
                "message": f"Error getting common paths: '{root_path}'. {str(e)}",
                "root_path": root_path,
                "max_depth": max_depth,
                "files": [],
                "folders": [],
                "total_files": 0,
                "total_folders": 0,
                "error": str(e)
            }
        }
