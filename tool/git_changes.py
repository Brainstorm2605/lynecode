#!/usr/bin/env python3
"""
Git changes reading tool for Lyne.

Provides functionality to read git status, diff, and other git change information.
Handles cases where git is not available or not in a git repository gracefully.
"""

import os
import subprocess
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from util.logging import get_logger, log_function_call, log_error, log_success, log_warning, log_info

logger = get_logger("git_changes")


def is_git_available() -> bool:
    """
    Check if git command is available in the system PATH.

    Returns:
        True if git is available, False otherwise
    """
    try:
        check_command = 'where' if os.name == 'nt' else 'command'
        check_args = ['git'] if os.name == 'nt' else ['-v', 'git']
        subprocess.check_call(
            [check_command] + check_args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            shell=os.name == 'nt'
        )
        return True
    except (subprocess.SubprocessError, OSError):
        return False


def is_git_repository(path: Path) -> bool:
    """
    Check if the given path is inside a git repository.

    Args:
        path: Path to check

    Returns:
        True if path is in a git repository, False otherwise
    """
    try:

        if (path / '.git').is_dir():
            return True

        result = subprocess.run(
            ['git', 'rev-parse', '--git-dir'],
            cwd=path,
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.returncode == 0
    except Exception:
        return False


def run_git_command(command: List[str], cwd: Path, timeout: int = 30) -> Optional[str]:
    """
    Run a git command safely with error handling.

    Args:
        command: Git command as list of arguments
        cwd: Working directory for the command
        timeout: Command timeout in seconds

    Returns:
        Command output as string, or None if failed
    """
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            errors='replace'
        )

        if result.returncode == 0:
            return result.stdout.strip()
        else:
            log_warning(
                f"Git command failed: {' '.join(command)} - {result.stderr.strip()}", logger)
            return None

    except subprocess.TimeoutExpired:
        log_warning(f"Git command timed out: {' '.join(command)}", logger)
        return None
    except Exception as e:
        log_error(e, f"Error running git command: {' '.join(command)}", logger)
        return None


def get_git_status(path: Path) -> Dict[str, Any]:
    """
    Get git status information.

    Args:
        path: Path to the git repository

    Returns:
        Dictionary with status information
    """
    status_info = {
        "staged_changes": [],
        "unstaged_changes": [],
        "untracked_files": [],
        "current_branch": None,
        "ahead_behind": None,
        "has_changes": False
    }

    branch_output = run_git_command(['git', 'branch', '--show-current'], path)
    if branch_output:
        status_info["current_branch"] = branch_output

    ahead_behind_output = run_git_command(
        ['git', 'status', '--porcelain=2', '--branch'], path)
    if ahead_behind_output:

        for line in ahead_behind_output.split('\n'):
            if line.startswith('# branch.ab '):
                parts = line.split()
                if len(parts) >= 4:
                    ahead = parts[2] if parts[2] != '+0' else None
                    behind = parts[3] if parts[3] != '-0' else None
                    if ahead or behind:
                        status_info["ahead_behind"] = {
                            "ahead": ahead,
                            "behind": behind
                        }
                break

    status_output = run_git_command(['git', 'status', '--porcelain'], path)
    if status_output:
        for line in status_output.split('\n'):
            if not line.strip():
                continue

            status_code = line[:2]
            file_path = line[3:]

            index_status = status_code[0]
            working_status = status_code[1]

            if index_status in ['A', 'M', 'D', 'R']:
                status_info["staged_changes"].append({
                    "file": file_path,
                    "status": index_status
                })

            if working_status in ['M', 'D', '?', 'A']:
                if working_status == '?':
                    status_info["untracked_files"].append(file_path)
                else:
                    status_info["unstaged_changes"].append({
                        "file": file_path,
                        "status": working_status
                    })

    status_info["has_changes"] = (
        len(status_info["staged_changes"]) > 0 or
        len(status_info["unstaged_changes"]) > 0 or
        len(status_info["untracked_files"]) > 0
    )

    return status_info


def get_git_diff(path: Path, staged: bool = False, file_path: Optional[str] = None) -> Optional[str]:
    """
    Get git diff output.

    Args:
        path: Path to the git repository
        staged: Whether to get staged changes (--cached)
        file_path: Specific file path to limit diff to

    Returns:
        Diff output as string, or None if failed
    """
    command = ['git', 'diff']

    if staged:
        command.append('--cached')

    if file_path:
        command.append(file_path)

    return run_git_command(command, path)


def get_git_log(path: Path, max_entries: int = 10, file_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get recent git commit history.

    Args:
        path: Path to the git repository
        max_entries: Maximum number of commits to return
        file_path: Specific file path to limit log to

    Returns:
        List of commit dictionaries
    """
    command = [
        'git', 'log',
        '--oneline',
        '-n', str(max_entries),
        '--pretty=format:%H|%an|%ae|%ad|%s'
    ]

    if file_path:
        command.extend(['--', file_path])

    log_output = run_git_command(command, path)
    if not log_output:
        return []

    commits = []
    for line in log_output.split('\n'):
        if not line.strip():
            continue

        parts = line.split('|', 4)
        if len(parts) >= 5:
            commits.append({
                "hash": parts[0],
                "author": parts[1],
                "email": parts[2],
                "date": parts[3],
                "message": parts[4]
            })

    return commits


def get_git_changes(
    path: str,
    include_status: bool = True,
    include_diff: bool = True,
    include_staged: bool = False,
    include_log: bool = False,
    max_log_entries: int = 5,
    specific_file: Optional[str] = None
) -> str:
    """
    Main function to get git changes information.

    Args:
        path: Path to check for git repository
        include_status: Whether to include git status
        include_diff: Whether to include unstaged changes diff
        include_staged: Whether to include staged changes diff
        include_log: Whether to include recent commit log
        max_log_entries: Maximum number of log entries
        specific_file: Specific file to limit changes to

    Returns:
        Formatted string with git changes information
    """
    try:
        log_function_call("get_git_changes", {
            "path": path,
            "include_status": include_status,
            "include_diff": include_diff,
            "include_staged": include_staged,
            "include_log": include_log,
            "max_log_entries": max_log_entries,
            "specific_file": specific_file
        }, logger)

        search_path = Path(path).resolve()

        if not is_git_available():
            log_warning("Git command is not available on this system", logger)
            return "Git is not available on this system. Please install git to use this functionality."

        if not is_git_repository(search_path):
            log_info(f"Path is not a git repository: {search_path}", logger)
            return f"No git repository found at: '{search_path}'. Please navigate to a git repository or initialize one with 'git init'."

        results = []

        def run_git_changes():
            nonlocal results
            try:
                status_info = None

                if include_status:
                    status_info = get_git_status(search_path)

                    status_lines = [f"Git Repository: {search_path}"]
                    if status_info["current_branch"]:
                        status_lines.append(
                            f"Current Branch: {status_info['current_branch']}")

                    if status_info["ahead_behind"]:
                        ahead_behind = status_info["ahead_behind"]
                        if ahead_behind["ahead"]:
                            status_lines.append(
                                f"Ahead: {ahead_behind['ahead']} commits")
                        if ahead_behind["behind"]:
                            status_lines.append(
                                f"Behind: {ahead_behind['behind']} commits")

                    if not status_info["has_changes"]:
                        status_lines.append(
                            "Working directory is clean - no changes detected")
                    else:
                        if status_info["staged_changes"]:
                            status_lines.append(
                                f"Staged Changes ({len(status_info['staged_changes'])} files):")
                            for change in status_info["staged_changes"][:20]:
                                status_lines.append(
                                    f"  {change['status']} {change['file']}")

                        if status_info["unstaged_changes"]:
                            status_lines.append(
                                f"Unstaged Changes ({len(status_info['unstaged_changes'])} files):")
                            for change in status_info["unstaged_changes"][:20]:
                                status_lines.append(
                                    f"  {change['status']} {change['file']}")

                        if status_info["untracked_files"]:
                            status_lines.append(
                                f"Untracked Files ({len(status_info['untracked_files'])} files):")
                            for file in status_info["untracked_files"][:20]:
                                status_lines.append(f"  ? {file}")

                    results.append('\n'.join(status_lines))

                if include_diff and (status_info is None or status_info["unstaged_changes"] or not specific_file):
                    diff_output = get_git_diff(
                        search_path, staged=False, file_path=specific_file)
                    if diff_output:
                        results.append(
                            f"\nUnstaged Changes Diff:\n{diff_output}")
                    elif specific_file:
                        results.append(
                            f"\nNo unstaged changes for file: {specific_file}")

                if include_staged and (status_info is None or status_info["staged_changes"] or not specific_file):
                    staged_diff_output = get_git_diff(
                        search_path, staged=True, file_path=specific_file)
                    if staged_diff_output:
                        results.append(
                            f"\nStaged Changes Diff:\n{staged_diff_output}")
                    elif specific_file:
                        results.append(
                            f"\nNo staged changes for file: {specific_file}")

                if include_log:
                    log_entries = get_git_log(
                        search_path, max_log_entries, specific_file)
                    if log_entries:
                        log_lines = ["\nRecent Commits:"]
                        for entry in log_entries:
                            log_lines.append(
                                f"  {entry['hash'][:8]} - {entry['message']} ({entry['author']})")
                        results.append('\n'.join(log_lines))
                    else:
                        results.append("\nNo commit history found")

            except Exception as e:
                log_error(
                    e, f"Error in git changes execution: {str(e)}", logger)

        import threading
        changes_thread = threading.Thread(target=run_git_changes)
        changes_thread.daemon = True
        changes_thread.start()

        changes_thread.join(timeout=60)

        if changes_thread.is_alive():
            partial_results = results[:] if results else []
            timeout_message = f"GIT CHANGES TIMEOUT: Git changes retrieval for '{path}' timed out. Found {len(partial_results)} sections so far."
            log_warning(timeout_message, logger)
            if partial_results:
                return f"{timeout_message}\n\n{'\n\n'.join(partial_results)}"
            else:
                return timeout_message

        if not results:
            return f"Git repository found at '{search_path}' but no changes information was requested."

        log_success(
            f"Git changes retrieved successfully for: {search_path}", logger)
        return '\n\n'.join(results)

    except Exception as e:
        log_error(e, f"Error getting git changes for path: {path}", logger)
        return f"Error retrieving git changes: {str(e)}"
