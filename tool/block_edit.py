#!/usr/bin/env python3
import os
import re
import difflib
import shutil
from pathlib import Path
from typing import Tuple, List, Dict

from util.logging import get_logger, log_function_call, log_error, log_success, log_warning

logger = get_logger("block_edit")

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    from rich.table import Table
    RICH_AVAILABLE = True
    console = Console()
except ImportError:
    RICH_AVAILABLE = False


class EditError(Exception):
    """Exception raised for errors during the edit process."""
    pass


def get_terminal_width() -> int:
    """Get current terminal width for formatting."""
    try:
        return shutil.get_terminal_size().columns
    except (OSError, AttributeError):
        return 80


def create_diff_summary(original: str, modified: str) -> Dict:
    """Analyze diff to determine display strategy and statistics."""
    original_lines = original.splitlines()
    modified_lines = modified.splitlines()

    matcher = difflib.SequenceMatcher(None, original_lines, modified_lines)
    additions = deletions = modifications = 0

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'replace':
            modifications += max(i2 - i1, j2 - j1)
        elif tag == 'delete':
            deletions += i2 - i1
        elif tag == 'insert':
            additions += j2 - j1

    return {
        'additions': additions,
        'deletions': deletions,
        'modifications': modifications,
    }


def generate_aesthetic_diff(original: str, modified: str, file_path: str):
    """Generate a beautiful side-by-side diff using rich.Table, showing only relevant context."""
    summary = create_diff_summary(original, modified)
    original_lines = original.splitlines()
    modified_lines = modified.splitlines()

    if not summary['additions'] and not summary['deletions'] and not summary['modifications']:
        return Panel("[dim]No changes detected.[/dim]", border_style="green", title="✅ NO CHANGES")

    table = Table.grid(expand=True, padding=(0, 1))
    table.add_column(f"[bold blue]Original[/bold blue]")
    table.add_column(f"[bold magenta]Modified[/bold magenta]")

    matcher = difflib.SequenceMatcher(
        None, original_lines, modified_lines, autojunk=False)
    grouped_opcodes = matcher.get_grouped_opcodes(n=5)

    for i, group in enumerate(grouped_opcodes):
        if i > 0:
            table.add_row(Text("...", style="dim cyan"),
                          Text("...", style="dim cyan"))

        for tag, i1, i2, j1, j2 in group:
            if tag == 'equal':
                for line in original_lines[i1:i2]:
                    table.add_row(Text(f"  {line}", style="dim"), Text(
                        f"  {line}", style="dim"))
            else:
                num_old = i2 - i1
                num_new = j2 - j1
                max_lines = max(num_old, num_new)
                for j in range(max_lines):
                    old_line_idx, new_line_idx = i1 + j, j1 + j

                    left = ""
                    if old_line_idx < i2:
                        original_line = original_lines[old_line_idx]
                        left = Text(f"- {original_line}", style="red")

                    right = ""
                    if new_line_idx < j2:
                        modified_line = modified_lines[new_line_idx]
                        right = Text(f"+ {modified_line}", style="green")

                    if old_line_idx < i2 and new_line_idx < j2 and tag == 'replace':
                        char_matcher = difflib.SequenceMatcher(
                            None, original_line, modified_line)
                        left = Text("- ", style="red")
                        right = Text("+ ", style="green")
                        for ctag, c1, c2, d1, d2 in char_matcher.get_opcodes():
                            if ctag == 'equal':
                                left.append(original_line[c1:c2])
                                right.append(modified_line[d1:d2])
                            elif ctag in ('delete', 'replace'):
                                left.append(
                                    original_line[c1:c2], style="on #880000")
                            if ctag in ('insert', 'replace'):
                                right.append(
                                    modified_line[d1:d2], style="on #008800")

                    table.add_row(left, right)

    header_text = Text()
    header_text.append("File: ", style="bold white")
    header_text.append(f"{file_path}\n", style="cyan")
    header_text.append("Changes: ", style="bold white")
    header_text.append(f"+{summary['additions']} ", style="green")
    header_text.append(f"-{summary['deletions']} ", style="red")

    return Panel(
        table,
        title="📋 CHANGE PREVIEW",
        border_style="blue",
        title_align="center",
        subtitle=header_text,
        subtitle_align="left"
    )


def generate_unified_diff(original: str, modified: str, file_path: str) -> str:
    """Generate unified diff for narrow terminals or fallback."""
    diff_lines = list(difflib.unified_diff(
        original.splitlines(),
        modified.splitlines(),
        fromfile=f"a/{Path(file_path).name}",
        tofile=f"b/{Path(file_path).name}",
        lineterm=""
    ))
    return '\n'.join(diff_lines)


def request_user_permission_with_diff(file_path: str, original: str, modified: str) -> bool:
    """
    Request user permission to apply changes with aesthetic diff display.
    Returns True if user accepts, False if rejected.
    """
    try:
        logger.info(f"Requesting user permission for changes to {file_path}")

        if RICH_AVAILABLE:
            console.print("\n")
            diff_display = generate_aesthetic_diff(
                original, modified, file_path)
            console.print(diff_display)
            console.print()

            try:
                console.print(
                    "\n[bold cyan]⏸️  Agent paused - waiting for your decision...[/bold cyan]")
                prompt = Text(
                    "Do you want to apply these changes? ", style="bold yellow")
                prompt.append("(y/n): ", style="dim yellow")
                response = console.input(prompt).strip().lower()
            except (EOFError, KeyboardInterrupt):
                console.print(
                    "\n[yellow]⚠️ Input cancelled. Treating as rejection.[/yellow]")
                return False

        else:
            diff_display = generate_unified_diff(original, modified, file_path)
            print("\n" + "="*80)
            print("📋 CHANGE PREVIEW (unified diff)")
            print("="*80)
            print(diff_display)
            print("="*80)
            print("\n⏸️  Agent paused - waiting for your decision...")

            try:
                response = input(
                    "Do you want to apply these changes? (y/n): ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print("\n⚠️ Input cancelled. Treating as rejection.")
                return False

        if response in ['y', 'yes']:
            if RICH_AVAILABLE:
                console.print(
                    "[bold green]✓ Changes accepted - applying now...[/bold green]")
            else:
                print("✓ Changes accepted - applying now...")
            return True
        else:
            if RICH_AVAILABLE:
                console.print("[bold red]✗ Changes rejected[/bold red]")
            else:
                print("✗ Changes rejected")
            return False

    except Exception as e:
        logger.error(f"Error in permission request: {str(e)}")
        if RICH_AVAILABLE:
            console.print(f"[red]❌ Error displaying diff: {str(e)}[/red]")
        else:
            print(f"❌ Error displaying diff: {str(e)}")
        return False


def find_closest_match(old_string: str, file_content: str) -> tuple[bool, str, int, int]:
    """
    Find the closest match for old_string in file_content if exact match fails
    Uses multiple strategies to find the best match

    Returns:
        (found_exact, best_match, start_pos, end_pos)
    """
    if old_string in file_content:
        start_pos = file_content.find(old_string)
        return True, old_string, start_pos, start_pos + len(old_string)

    normalized_old = old_string.replace('\r\n', '\n')
    normalized_content = file_content.replace('\r\n', '\n')
    if normalized_old in normalized_content:
        start_pos = normalized_content.find(normalized_old)
        return True, normalized_old, start_pos, start_pos + len(normalized_old)

    lines = normalized_old.split('\n')
    patterns = []

    for line in lines:
        indent_match = re.match(r'^(\s*)', line)
        indent = indent_match.group(1) if indent_match else ''

        rest = re.escape(line.strip())
        rest = re.sub(r'\\ +', r'\\s+', rest)

        patterns.append(f"{re.escape(indent)}{rest}")

    flexible_pattern = r'\s*'.join(patterns)

    match = re.search(flexible_pattern, normalized_content, re.DOTALL)
    if match:
        return False, match.group(0), match.start(), match.end()

    sequence_matcher = difflib.SequenceMatcher(
        None, normalized_old, normalized_content)
    match = sequence_matcher.find_longest_match(
        0, len(normalized_old), 0, len(normalized_content))

    if match.size > len(normalized_old) * 0.8:
        return False, normalized_content[match.b:match.b+match.size], match.b, match.b+match.size

    return False, "", -1, -1


def calculate_edit(file_path: str, old_string: str, new_string: str) -> tuple[str, str, bool]:
    """
    Calculate the edit and generate a diff preview.

    Args:
        file_path: Path to the file to edit
        old_string: Text to replace (must include context)
        new_string: New text to insert

    Returns:
        (original_content, new_content, is_new_file)

    Raises:
        EditError: If the edit cannot be performed
    """
    p = Path(file_path)
    is_new_file = False

    if old_string == "":
        if p.exists():
            raise EditError(
                f"Cannot create new file: {file_path} already exists")
        original_content = ""
        new_content = new_string
        is_new_file = True
    else:
        if not p.exists():
            raise EditError(f"File not found: {file_path}")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
        except Exception as e:
            raise EditError(f"Failed to read file {file_path}: {str(e)}")

        found_exact, matched_text, start_pos, end_pos = find_closest_match(
            old_string, original_content)

        if start_pos == -1:
            raise EditError(f"Could not find text to replace in {file_path}")

        if not found_exact:
            logger.warning(f"Using fuzzy match for edit in {file_path}")

        new_content = original_content[:start_pos] + \
            new_string + original_content[end_pos:]

    return original_content, new_content, is_new_file


def generate_diff(original: str, modified: str, file_path: str) -> str:
    """Generate a diff between original and modified content."""
    diff = difflib.unified_diff(
        original.splitlines(keepends=True),
        modified.splitlines(keepends=True),
        fromfile=f"a/{file_path}",
        tofile=f"b/{file_path}"
    )
    return ''.join(diff)


def apply_edit(file_path: str, new_content: str, is_new_file: bool = False) -> bool:
    """
    Apply the edit to the file.

    Args:
        file_path: Path to the file to edit
        new_content: New content to write
        is_new_file: Whether this is a new file

    Returns:
        True if successful
    """
    temp_path = f"{file_path}.tmp"

    try:
        p = Path(file_path)
        p.parent.mkdir(parents=True, exist_ok=True)

        with open(temp_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

        os.replace(temp_path, file_path)
        return True
    except Exception as e:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass
        raise EditError(f"Failed to write to {file_path}: {str(e)}")


def block_edit_file(file_path: str, old_string: str, new_string: str) -> tuple[bool, str]:
    """
    Main function to perform a block-based edit with user permission.

    Args:
        file_path: Path to the file to edit
        old_string: Text to replace (must include context)
        new_string: New text to insert

    Returns:
        (success, message)
    """
    try:
        log_function_call("block_edit_file", {
            'file_path': file_path,
            'old_string_length': len(old_string),
            'new_string_length': len(new_string)
        }, logger)

        if Path(file_path).exists():
            try:
                from vcs.backup_manager import BackupManager
                backup_mgr = BackupManager()
                backup_mgr.backup_file(file_path)
            except Exception:
                pass

        original_content, new_content, is_new_file = calculate_edit(
            file_path, old_string, new_string)

        if not is_new_file:
            if not request_user_permission_with_diff(file_path, original_content, new_content):
                rejection_message = (
                    "❌ User rejected the proposed changes. This suggests one of several possibilities:\n\n"
                    "• The changes may be targeting the wrong file or location\n"
                    "• The modifications don't align with the user's actual intent\n"
                    "• There may be errors, duplications, or unintended side effects in the proposed changes\n"
                    "• The scope of changes might be too broad or too narrow\n\n"
                    "Let's reconsider the approach:\n"
                    "1. Are we editing the correct file and location?\n"
                    "2. Do the proposed changes match what you're trying to achieve?\n"
                    "3. Should we break this into smaller, more targeted changes?\n"
                    "4. Is there a different approach that would better serve the needs?\n\n"
                    "Let's think about this differently and find a solution that works."
                )
                logger.info(f"User rejected changes to {file_path}")
                return False, rejection_message

            diff = generate_diff(original_content, new_content, file_path)
            if diff:
                logger.info(
                    f"Applying changes to {Path(file_path).name}:\n")
            else:
                logger.warning("No changes detected in the edit")
                return False, f"No changes detected in the edit\n📊 Tool call parameters: file_path='{file_path}', old_string={repr(old_string)}, new_string={repr(new_string)}"
        else:
            logger.info(f"Creating new file: {file_path}")

        apply_edit(file_path, new_content, is_new_file)

        action = "Created" if is_new_file else "Updated"
        success_message = f"✅ {action} {Path(file_path).name} successfully\n📊 Tool call parameters: file_path='{file_path}', old_string={repr(old_string)}, new_string={repr(new_string)}"
        logger.info(f"✓ {action} {file_path} successfully")
        log_success(f"{action} {file_path} successfully", logger)

        return True, success_message

    except EditError as e:
        log_error(e, f"Edit error for {file_path}", logger)
        return False, f"{str(e)}\n📊 Tool call parameters: file_path='{file_path}', old_string={repr(old_string)}, new_string={repr(new_string)}"
    except Exception as e:
        log_error(
            e, f"Unexpected error in block_edit_file for {file_path}", logger)
        return False, f"Unexpected error: {str(e)}\n📊 Tool call parameters: file_path='{file_path}', old_string={repr(old_string)}, new_string={repr(new_string)}"
