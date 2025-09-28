#!/usr/bin/env python3
import os
import glob
import fnmatch
from pathlib import Path
from datetime import datetime

from util.logging import get_logger, log_function_call, log_error, log_success, log_warning

logger = get_logger("read_many")


DEFAULT_EXCLUDES = [
    '**/node_modules/**',
    '**/.git/**',
    '**/.vscode/**',
    '**/.idea/**',
    '**/dist/**',
    '**/build/**',
    '**/coverage/**',
    '**/__pycache__/**',
    '**/lynecode/**',
    '**/time_machine/**',
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
    '**/.env',
]

DEFAULT_OUTPUT_SEPARATOR_FORMAT = '--- {filePath} ---'


def should_ignore_file(filepath: str, exclude_patterns: list = None) -> bool:
    """
    Check if a file should be ignored based on glob patterns.
    """
    if not exclude_patterns:
        return False

    for pattern in exclude_patterns:
        if fnmatch.fnmatch(filepath, pattern):
            return True
    return False


def get_file_info(filepath: str) -> dict:
    """
    Get detailed information about a file.
    """
    try:
        stat = os.stat(filepath)
        return {
            'name': os.path.basename(filepath),
            'path': filepath,
            'size': stat.st_size,
            'modified': datetime.fromtimestamp(stat.st_mtime),
            'is_dir': os.path.isdir(filepath),
            'readable': os.access(filepath, os.R_OK)
        }
    except (OSError, IOError) as e:
        return {
            'name': os.path.basename(filepath),
            'path': filepath,
            'error': str(e)
        }


def read_file_content(filepath: str) -> tuple[bool, str, str]:
    """
    Read file content with error handling.
    Returns (success, content, error_message)
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            return True, content, ""
    except UnicodeDecodeError:
        try:

            with open(filepath, 'r', encoding='latin-1') as f:
                content = f.read()
                return True, content, ""
        except Exception as e:
            return False, "", f"Failed to read file: {e}"
    except Exception as e:
        return False, "", f"Failed to read file: {e}"


def read_many_files(paths: list, include: list = None, exclude: list = None,
                    use_default_excludes: bool = True, recursive: bool = True) -> str:
    """
    Read multiple files using glob patterns and concatenate their content.

    Args:
        paths: List of glob patterns or file paths
        include: Additional glob patterns to include
        exclude: Glob patterns to exclude
        use_default_excludes: Whether to apply default exclusion patterns
        recursive: Whether to search recursively (controlled by ** in glob patterns)

    Returns:
        Combined content from all files as a string, empty string if no files found or on error
    """
    try:
        log_function_call("read_many_files", {
            'paths': paths,
            'include': include,
            'exclude': exclude,
            'use_default_excludes': use_default_excludes,
            'recursive': recursive
        }, logger)

        if not paths:
            log_error(Exception("No search paths provided"),
                      "No search paths provided", logger)
            return ""

        search_patterns = paths + (include or [])
        if not search_patterns:
            log_error(Exception("No search patterns provided"),
                      "No search patterns provided", logger)
            return ""

        effective_excludes = []
        if use_default_excludes:
            effective_excludes.extend(DEFAULT_EXCLUDES)
        if exclude:
            effective_excludes.extend(exclude)

        processed_files = []
        skipped_files = []
        all_content = []

        for pattern in search_patterns:

            pattern = pattern.replace('\\', '/')

            matching_files = glob.glob(pattern, recursive=recursive)

            for filepath in matching_files:

                if should_ignore_file(filepath, effective_excludes):
                    skipped_files.append({
                        'path': filepath,
                        'reason': 'excluded by pattern'
                    })
                    continue

                file_info = get_file_info(filepath)

                if file_info.get('is_dir', False):
                    continue

                if 'error' in file_info:
                    skipped_files.append({
                        'path': filepath,
                        'reason': file_info['error']
                    })
                    continue

                success, content, error = read_file_content(filepath)

                if success:

                    separator = DEFAULT_OUTPUT_SEPARATOR_FORMAT.replace(
                        '{filePath}', filepath)
                    all_content.append(f"{separator}\n\n{content}\n\n")
                    processed_files.append(filepath)
                else:
                    skipped_files.append({
                        'path': filepath,
                        'reason': error
                    })

        processed_files.sort()

        if not processed_files and not skipped_files:
            log_warning("No files found matching the patterns", logger)
            return ""

        combined_content = "".join(all_content)

        log_success(f"Successfully read {len(processed_files)} files", logger)
        return combined_content

    except Exception as e:
        log_error(e, "Error in read_many_files", logger)
        return ""
