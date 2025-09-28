#!/usr/bin/env python3
"""
High-performance, parallel ast-grep search utility using a pure Python approach.

This module leverages the `ast-grep-py` library and Python's `concurrent.futures`
to perform multi-threaded, folder-based structural searches. It discovers all
files first, then distributes the CPU-intensive parsing work across multiple
processor cores for significant speed improvements on large codebases.
"""

import os
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import List, Dict, Any
from ast_grep_py import SgRoot, Config
from util.logging import get_logger, log_error, log_info, log_warning

logger = get_logger("ast_grep_parallel")

DEFAULT_EXCLUDE_DIRS = {".git", "node_modules", "__pycache__", ".svn", ".hg", "venv", "dist", "build", 'build',
                        'dist', 'target', '.next', '.nuxt', 'vendor', 'packages', 'Lib', 'library', 'libraries',
                        'deps', 'dependencies', 'lynecode', '.mypy_cache', '.tox', '.coverage', 'htmlcov'}
BINARY_FILE_EXTENSIONS = {'.pyc', '.pyo', '.o', '.a', '.so', '.dll',
                          '.exe', '.img', '.iso', '.zip', '.tar', '.gz', 'gif', 'mp4'}


def _is_supported_language(file_path: Path) -> bool:
    """Check if the file extension corresponds to a language supported by ast grep."""
    supported_extensions = {
        '.py', '.js', '.jsx', '.ts', '.tsx', '.go', '.java', '.c', '.h', '.cpp',
        '.hpp', '.rs', '.rb', '.kt', '.swift', '.scala', '.html', '.css', '.scss'
    }
    return file_path.suffix.lower() in supported_extensions


def _search_one_file(file_path: Path, pattern: str, lang: str = None) -> List[Dict[str, Any]]:
    """
    Worker function to perform an ast-grep search on a single file.
    Designed to be run in a separate process.
    """
    try:
        source_code = file_path.read_text(encoding='utf-8')
        language_to_use = lang or file_path.suffix[1:]

        sg = SgRoot(source_code, language_to_use)
        root_node = sg.root()

        search_config = Config(rule={'pattern': pattern})
        matches = root_node.find_all(search_config)

        file_results = []
        for match in matches:
            node_range = match.range()
            file_results.append({
                'file': str(file_path),
                'line_number': node_range.start.line + 1,
                'content': match.text().strip()
            })
        return file_results

    except (UnicodeDecodeError, IOError):
        return []
    except Exception:
        return []


def ast_grep_search(
    pattern: str,
    path: str,
    max_results: int = 100,
    lang: str = None
) -> list:
    """
    Performs a high-speed, parallel structural search using the ast-grep-py library.

    Args:
        pattern: The AST pattern to search for (e.g., 'class $NAME: $_').
        path: The directory or file path to search in.
        max_results: The maximum number of results to return.
        lang: The programming language to parse. If omitted, it's inferred from file extensions.

    Returns:
        A list of dictionaries, where each dictionary represents a match.
    """
    search_path = Path(path).resolve()
    if not search_path.exists():
        log_error(Exception(
            f"Path does not exist: {search_path}"), "Path does not exist", logger)
        return []

    if not pattern or not pattern.strip():
        log_error(Exception("Empty AST pattern provided"),
                  "Empty pattern", logger)
        return []
    files_to_search = []
    if search_path.is_dir():
        for root, dirs, files in os.walk(search_path, topdown=True):
            dirs[:] = [d for d in dirs if d not in DEFAULT_EXCLUDE_DIRS]
            for file in files:
                file_path = Path(root) / file
                if file_path.suffix.lower() not in BINARY_FILE_EXTENSIONS and _is_supported_language(file_path):
                    files_to_search.append(file_path)
    elif search_path.is_file():
        if search_path.suffix.lower() not in BINARY_FILE_EXTENSIONS and _is_supported_language(search_path):
            files_to_search.append(search_path)

    if not files_to_search:
        log_info("No matching files found to search.", logger)
        return []

    log_info(
        f"Starting parallel search for '{pattern}' across {len(files_to_search)} files...", logger)

    all_results = []
    with ProcessPoolExecutor() as executor:
        future_to_file = {executor.submit(
            _search_one_file, f, pattern, lang): f for f in files_to_search}

        try:
            for future in as_completed(future_to_file):
                if len(all_results) >= max_results:
                    executor.shutdown(wait=False, cancel_futures=True)
                    break

                try:
                    matches = future.result()
                    if matches:
                        all_results.extend(matches)
                except Exception as exc:
                    file_path = future_to_file[future]
                    log_warning(
                        f"Worker process for {file_path} generated an exception: {exc}", logger)
        except KeyboardInterrupt:
            log_warning(
                "Search cancelled by user. Shutting down worker processes...", logger)
            executor.shutdown(wait=False, cancel_futures=True)
            return all_results[:max_results]

    log_info(
        f"Parallel search complete. Found {len(all_results)} total matches.", logger)
    return all_results[:max_results]
