#!/usr/bin/env python3
import os
import re
import subprocess
import asyncio
from pathlib import Path

import aiofiles
from util.logging import get_logger, log_error, log_warning, log_info

logger = get_logger("grep")


def is_likely_text_file(file_path: Path) -> bool:
    """Check if a file is likely to be a text file"""
    try:
        with open(file_path, 'rb') as f:
            chunk = f.read(1024)
            if b'\x00' in chunk:
                return False
    except Exception:
        return False
    return True


def escape_regex_pattern(pattern: str) -> str:
    """Escape special regex characters for literal string matching"""
    special_chars = r'[.*+?^${}()|[\]\\]'
    escaped_pattern = ''
    i = 0
    while i < len(pattern):
        if pattern[i] == '\\' and i + 1 < len(pattern):

            escaped_pattern += pattern[i:i+2]
            i += 2
        elif pattern[i] in special_chars:
            escaped_pattern += '\\' + pattern[i]
            i += 1
        else:
            escaped_pattern += pattern[i]
            i += 1
    return escaped_pattern


def smart_pattern_handling(pattern: str) -> tuple[str, bool]:
    """Smart pattern handling - detect if user wants literal or regex search"""

    regex_chars = r'[.*+?^${}()|[\]\\]'
    has_regex_chars = any(char in pattern for char in regex_chars)

    if pattern.startswith('/') and pattern.endswith('/') and len(pattern) > 2:
        return pattern[1:-1], True

    if has_regex_chars:
        return pattern, True

    return escape_regex_pattern(pattern), False


def is_simple_literal(pattern):
    special_chars = r'[.*+?^${}()|[\]\\]'
    has_special = any(char in pattern for char in special_chars)
    return not has_special and len(pattern) >= 3


def collect_files_scandir(path, exclude_dirs_lower, include_regex):
    """Fast file collection using os.scandir()"""
    files_to_search = []

    def scan_directory(current_path):
        try:
            for entry in os.scandir(current_path):
                if entry.is_dir():
                    if entry.name.lower() not in exclude_dirs_lower:
                        scan_directory(entry.path)
                elif entry.is_file():
                    if include_regex and not include_regex.match(entry.name):
                        continue

                    file_path = Path(entry.path)
                    if is_likely_text_file(file_path):
                        files_to_search.append(file_path)
        except (OSError, PermissionError):
            pass

    scan_directory(str(path))
    return files_to_search


def grep_git(pattern: str, path: Path, max_results: int = 100, include_pattern: str = None) -> list:
    """
    Use git grep for fast searching in git repositories

    Args:
        pattern: The regex pattern to search for
        path: Path to the root directory to search in
        case_sensitive: Whether the search should be case sensitive (kept for compatibility, always uses case-insensitive)
        max_results: Maximum number of results to return
        include_pattern: Optional glob pattern to filter files

    Returns:
        List of match dictionaries
    """
    results = []
    try:
        if not (path / '.git').exists():
            return results

        cmd = ['git', 'grep', '-n', '--untracked', '-E', '-i']
        cmd.append(pattern)

        if include_pattern:
            cmd.extend(['--', include_pattern])

        process = subprocess.run(
            cmd, cwd=path, capture_output=True, text=True, timeout=160)
        if process.returncode not in [0, 1]:
            return results

        if not process.stdout:
            return results
        lines = process.stdout.splitlines()

        for line in lines[:max_results]:
            first_colon = line.find(':')
            if first_colon == -1:
                continue

            second_colon = line.find(':', first_colon + 1)
            if second_colon == -1:
                continue

            file_path = line[:first_colon]
            line_num = line[first_colon + 1:second_colon]
            content = line[second_colon + 1:]

            try:
                line_num_int = int(line_num)
                full_path = (path / file_path).resolve()

                if not full_path.exists():
                    continue

                results.append({
                    'file': str(full_path),
                    'line_number': line_num_int,
                    'content': content.strip()
                })
            except ValueError:
                continue

    except Exception as e:
        log_warning(f"Git grep failed: {str(e)}", logger)

    return results


def grep_system(
    pattern: str,
    path: Path,
    max_results: int = 100,
    include_pattern: str = None,
    exclude_dirs: list = None
) -> list:
    """
    Try to use system grep for searching

    Args:
        pattern: The regex pattern to search for
        path: Path to the root directory to search in
        case_sensitive: Whether the search should be case sensitive (kept for compatibility, always uses case-insensitive)
        max_results: Maximum number of results to return
        include_pattern: Optional glob pattern to filter files
        exclude_dirs: List of directories to exclude

    Returns:
        List of match dictionaries
    """
    results = []

    try:
        cmd = ['grep', '-r', '-n', '-E', '-i']

        if exclude_dirs:
            for dir_name in exclude_dirs:
                cmd.append(f'--exclude-dir={dir_name}')

        if include_pattern:
            cmd.append(f'--include={include_pattern}')

        cmd.extend([pattern, '.'])

        process = subprocess.Popen(
            cmd,
            cwd=path,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            errors='replace'
        )

        try:
            stdout, stderr = process.communicate(timeout=160)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate()
            log_warning(f"System grep timed out after 160 seconds", logger)
            return results

        if process.returncode not in [0, 1]:
            return results

        if not stdout:
            return results
        lines = stdout.splitlines()

        for line in lines[:max_results]:
            first_colon = line.find(':')
            if first_colon == -1:
                continue

            second_colon = line.find(':', first_colon + 1)
            if second_colon == -1:
                continue

            file_path = line[:first_colon]
            line_num = line[first_colon + 1:second_colon]
            content = line[second_colon + 1:]

            try:
                line_num_int = int(line_num)
                full_path = (path / file_path).resolve()

                if not full_path.exists() or not str(full_path).startswith(str(path)):
                    continue

                results.append({
                    'file': str(full_path),
                    'line_number': line_num_int,
                    'content': content.strip()
                })
            except ValueError:
                continue

    except subprocess.SubprocessError as e:
        log_warning(f"System grep subprocess error: {str(e)}", logger)
    except Exception as e:
        log_warning(f"System grep failed: {str(e)}", logger)

    return results


def grep_python(
    pattern: str,
    path: Path,
    max_results: int = 100,
    include_pattern: str = None,
    exclude_dirs: list = None
) -> list:
    """
    Pure Python implementation of grep as a final fallback

    Args:
        pattern: The regex pattern to search for
        path: Path to the root directory to search in
        case_sensitive: Whether the search should be case sensitive (kept for compatibility, always uses case-insensitive)
        max_results: Maximum number of results to return
        include_pattern: Optional glob pattern to filter files
        exclude_dirs: List of directories to exclude

    Returns:
        List of match dictionaries
    """
    results = []

    flags = re.IGNORECASE
    try:
        regex = re.compile(pattern, flags)
    except re.error as e:
        log_error(
            e, f"Invalid regex pattern in Python grep: {pattern}", logger)
        return results

    include_regex = None
    if include_pattern:
        try:
            include_regex_pattern = include_pattern.replace('.', r'\.')
            include_regex_pattern = include_regex_pattern.replace('*', '.*')
            include_regex_pattern = include_regex_pattern.replace('?', '.')
            if '{' in include_pattern and ',' in include_pattern and '}' in include_pattern:
                parts = re.findall(r'\{([^}]+)\}', include_pattern)
                for part in parts:
                    options = part.split(',')
                    options_pattern = '|'.join(opt.strip() for opt in options)
                    include_regex_pattern = include_regex_pattern.replace(
                        f'{{{part}}}', f'({options_pattern})')
            include_regex = re.compile(
                f"^{include_regex_pattern}$", re.IGNORECASE)
        except re.error:
            log_warning(
                f"Invalid include pattern: {include_pattern}. Ignoring.", logger)
            include_regex = None

    if exclude_dirs is None:
        exclude_dirs = [".git", "node_modules", "__pycache__", ".svn", ".hg", "venv", "lynecode", 'Lib', 'library',
                        'libraries', 'deps', 'node_modules', 'build', 'dist', 'target', '.next', '.nuxt', 'vendor', 'packages', 'time_machine']

    exclude_dirs_lower = [d.lower() for d in exclude_dirs]

    files_to_search = collect_files_scandir(
        path, exclude_dirs_lower, include_regex)

    if len(files_to_search) > 30:
        try:
            return asyncio.run(grep_python_async(files_to_search, regex, max_results, path))
        except ImportError:
            return grep_python_parallel(files_to_search, regex, max_results, path)
    else:
        return grep_python_sequential(files_to_search, regex, max_results, path)


def grep_python_sequential(files_to_search: list, regex: re.Pattern, max_results: int, path: Path) -> list:
    """Sequential file processing for small projects"""
    results = []

    for file_path in files_to_search:
        if len(results) >= max_results:
            break

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line_num, line in enumerate(f, 1):
                    if regex.search(line):
                        full_path = file_path.resolve()
                        if str(full_path).startswith(str(path)):
                            results.append({
                                'file': str(full_path),
                                'line_number': line_num,
                                'content': line.strip()
                            })

                            if len(results) >= max_results:
                                break
        except (IOError, UnicodeDecodeError, PermissionError) as e:
            log_warning(f"Error reading {file_path}: {str(e)}", logger)
            continue
        except Exception as e:
            log_warning(
                f"Unexpected error processing {file_path}: {str(e)}", logger)
            continue

    return results


def grep_python_parallel(files_to_search: list, regex: re.Pattern, max_results: int, path: Path) -> list:
    """Parallel file processing for large projects"""
    import concurrent.futures

    results = []

    def search_single_file(file_path: Path) -> list:
        """Search a single file and return matches"""
        file_results = []
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line_num, line in enumerate(f, 1):
                    if regex.search(line):
                        full_path = file_path.resolve()
                        if str(full_path).startswith(str(path)):
                            file_results.append({
                                'file': str(full_path),
                                'line_number': line_num,
                                'content': line.strip()
                            })
        except Exception:
            pass
        return file_results

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        future_to_file = {executor.submit(search_single_file, file_path): file_path
                          for file_path in files_to_search}

        for future in concurrent.futures.as_completed(future_to_file):
            if len(results) >= max_results:
                for f in future_to_file:
                    f.cancel()
                break

            file_results = future.result()
            results.extend(file_results)

    return results[:max_results]


def grep_literal_search(pattern, path, max_results, include_pattern, exclude_dirs):
    if exclude_dirs is None:
        exclude_dirs = [".git", "node_modules", "__pycache__", ".svn", ".hg", "venv", "lynecode", 'Lib', 'library',
                        'libraries', 'deps', 'node_modules', 'build', 'dist', 'target', '.next', '.nuxt', 'vendor', 'packages', 'time_machine']

    exclude_dirs_lower = [d.lower() for d in exclude_dirs]

    include_regex = None
    if include_pattern:
        include_regex_pattern = include_pattern.replace('.', r'\.')
        include_regex_pattern = include_regex_pattern.replace('*', '.*')
        include_regex_pattern = include_regex_pattern.replace('?', '.')
        if '{' in include_pattern and ',' in include_pattern and '}' in include_pattern:
            parts = re.findall(r'\{([^}]+)\}', include_pattern)
            for part in parts:
                options = part.split(',')
                options_pattern = '|'.join(opt.strip() for opt in options)
                include_regex_pattern = include_regex_pattern.replace(
                    f'{{{part}}}', f'({options_pattern})')
        include_regex = re.compile(f"^{include_regex_pattern}$", re.IGNORECASE)

    files_to_search = collect_files_scandir(
        path, exclude_dirs_lower, include_regex)

    results = []

    for file_path in files_to_search:
        if len(results) >= max_results:
            break

        file_results = search_literal_in_file(file_path, pattern)
        results.extend(file_results)

        if len(results) >= max_results:
            results = results[:max_results]
            break

    return results


def search_literal_in_file(file_path, pattern):
    results = []

    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            lines = content.split('\n')

            for line_idx, line in enumerate(lines):
                pos = line.lower().find(pattern.lower())
                if pos != -1:
                    results.append({
                        'file': str(file_path),
                        'line_number': line_idx + 1,
                        'content': line.strip()
                    })

    except (IOError, UnicodeDecodeError, PermissionError):
        pass

    return results


async def search_file_async(file_path, regex):
    results = []

    try:
        async with aiofiles.open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            line_num = 1

            async for line in f:
                if regex.search(line):
                    results.append({
                        'file': str(file_path),
                        'line_number': line_num,
                        'content': line.strip()
                    })
                line_num += 1

    except (IOError, UnicodeDecodeError, PermissionError):
        pass

    return results


def get_optimal_concurrency():
    cpu_count = os.cpu_count() or 4

    if cpu_count <= 4:
        return cpu_count * 6
    elif cpu_count <= 8:
        return cpu_count * 4
    else:
        return cpu_count * 3


async def grep_python_async(files_to_search, regex, max_results, path):
    optimal_concurrency = get_optimal_concurrency()
    semaphore = asyncio.Semaphore(optimal_concurrency)
    tasks = []

    async def search_file(file_path):
        async with semaphore:
            return await search_file_async(file_path, regex)

    tasks = [search_file(file) for file in files_to_search]
    results_lists = await asyncio.gather(*tasks)

    all_results = []
    for results in results_lists:
        all_results.extend(results)

    all_results.sort(key=lambda x: x['file'])
    return all_results


def is_command_available(command: str) -> bool:
    """
    Check if a command is available in the system's PATH.

    Args:
        command: The command to check

    Returns:
        True if the command is available, False otherwise
    """
    try:
        check_command = 'where' if os.name == 'nt' else 'command'
        check_args = [command] if os.name == 'nt' else ['-v', command]
        subprocess.check_call(
            [check_command] + check_args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            shell=os.name == 'nt'
        )
        return True
    except (subprocess.SubprocessError, OSError):
        return False


def grep_search(
    pattern: str,
    path: str,
    max_results: int = 100,
    include_pattern: str = None,
    exclude_dirs: list = None
) -> list:
    """
    Main grep function with multiple fallback strategies.
    All searches are case-insensitive for better usability.

    Args:
        pattern: Regular expression pattern to search for
        path: Path to search in (required)
        max_results: Maximum number of results to return (default: 100)
        include_pattern: Optional glob pattern to filter files (e.g., "*.py", "*.{js,ts}")
        exclude_dirs: List of directories to exclude from search

    Returns:
        List of match dictionaries, empty list if no matches found or on error
    """
    try:
        if exclude_dirs is None:
            exclude_dirs = [".git", "node_modules", "__pycache__", ".svn", ".hg", "venv", "lynecode", 'Lib', 'library',
                            'libraries', 'deps', 'node_modules', 'build', 'dist', 'target', '.next', '.nuxt', 'vendor', 'packages', 'time_machine']

        search_path = Path(path).resolve()

        if not search_path.exists():
            log_error(Exception(
                f"Path does not exist: {search_path}"), "Path does not exist", logger)
            return []

        search_pattern, is_regex = smart_pattern_handling(pattern)

        results = []

        git_available = (
            search_path / '.git').is_dir() and is_command_available('git')
        grep_available = is_command_available('grep')

        if is_simple_literal(search_pattern) and not is_regex:
            search_type = 'literal'
        else:
            search_type = 'regex'

        def run_grep_search():
            nonlocal results
            try:
                if git_available:
                    results = grep_git(search_pattern, search_path,
                                       max_results, include_pattern)
                    if results:
                        log_info(
                            f"Git grep found {len(results)} results", logger)

                if not results and grep_available:
                    results = grep_system(
                        search_pattern, search_path, max_results,
                        include_pattern, exclude_dirs
                    )
                    if results:
                        log_info(
                            f"System grep found {len(results)} results", logger)

                if not results:
                    log_info("Using Python grep", logger)
                    if search_type == 'literal':
                        results = grep_literal_search(
                            search_pattern, search_path, max_results, include_pattern, exclude_dirs)
                    else:
                        results = grep_python(
                            search_pattern, search_path, max_results,
                            include_pattern, exclude_dirs
                        )
                    if results:
                        log_info(
                            f"Python grep found {len(results)} results", logger)
            except Exception as e:
                log_error(
                    e, f"Error in grep search execution: {str(e)}", logger)

        import threading
        search_thread = threading.Thread(target=run_grep_search)
        search_thread.daemon = True
        search_thread.start()

        search_thread.join(timeout=60)

        if search_thread.is_alive():
            partial_results = results[:max_results] if results else []
            timeout_message = f"GREP TIMEOUT: Pattern '{pattern}' search timed out. Found {len(partial_results)} results so far."
            log_warning(timeout_message, logger)
            return {
                "status": "timeout",
                "message": timeout_message,
                "results": partial_results,
                "pattern": pattern,
                "path": path,
                "found_count": len(partial_results)
            }

        return results

    except Exception as e:
        log_error(e, f"Error in grep_search for pattern: {pattern}", logger)
        return []
