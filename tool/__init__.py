#!/usr/bin/env python3
"""
Lyne Tool Package

A comprehensive collection of file and text manipulation tools for the Lyne project.
All tools include comprehensive error handling, logging, and return consistent result formats.
"""

from .create import create_file, create_folder
from .delete import delete_file, delete_folder
from .edit import write_lines, replace_lines, delete_lines
from .block_edit import block_edit_file, EditError
from .read import fetch_content
from .read_many import read_many_files
from .grep import grep_search
from .search_and_read import search_and_read
from .search_index import search_index
from .ast_grep import ast_grep_search
from .directory_utils import (
    file_exists, folder_exists, get_folder_structure, get_file_info,
    find_files_by_pattern, get_path_type, get_common_paths
)
from .git_changes import get_git_changes
from .linting_checker import linting_checker
from .terminal import run_terminal_command
from .web_search import web_search
from .web_reader import read_web_page
from .semgrep import semgrep_scan

__all__ = [
    # File creation
    'create_file',
    'create_folder',

    # File deletion
    'delete_file',
    'delete_folder',

    # Line-based editing
    'write_lines',
    'replace_lines',
    'delete_lines',

    # Block-based editing
    'block_edit_file',
    'EditError',

    # File reading
    'fetch_content',
    'read_many_files',

    # Text searching
    'grep_search',

    # Hybrid search and read
    'search_and_read',
    'search_index',

    # AST-based search
    'ast_grep_search',

    # Directory understanding
    'file_exists',
    'folder_exists',
    'get_folder_structure',
    'get_file_info',
    'find_files_by_pattern',
    'get_path_type',
    'get_common_paths',

    # Git changes
    'get_git_changes',

    # Code linting
    'linting_checker',

    # Terminal command runner
    'run_terminal_command',

    # Web tools
    'web_search',
    'read_web_page',

    # Security/static analysis
    'semgrep_scan',
]

try:
    from util.logging import setup_logging
    setup_logging()
except ImportError:
    pass
