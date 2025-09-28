import os
from pathlib import Path
from util.logging import get_logger, log_function_call, log_error, log_success

logger = get_logger("edit")

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    RICH_AVAILABLE = True
    console = Console()
except ImportError:
    RICH_AVAILABLE = False


def get_write_lines_info_display(file_path: str, line_number: int, content: str) -> str:
    """Get formatted display information about content to be written."""
    try:
        lines = len(content.splitlines())
        chars = len(content)
        return f"Insert at line {line_number}: {lines} lines"
    except Exception:
        return f"Insert at line {line_number}: Unknown content"


def request_write_lines_permission(file_path: str, line_number: int, content: str) -> bool:
    """Request user permission to write lines with detailed information."""
    path = Path(file_path).resolve()
    file_name = path.name
    operation_info = get_write_lines_info_display(
        file_path, line_number, content)

    try:
        if RICH_AVAILABLE and console:

            permission_text = Text()
            permission_text.append(
                f"File_name: {file_name}\n", style="bold blue")

            display_path = file_path if len(
                file_path) <= 45 else "..." + file_path[-42:]
            permission_text.append(
                f"File_path: {display_path}\n", style="dim white")
            display_info = operation_info if len(
                operation_info) <= 45 else operation_info[:42] + "..."
            permission_text.append(f"\n{display_info}", style="dim cyan")
            permission_text.append(
                "\nThis action cannot be undone!", style="dim red")

            console.print(Panel(
                permission_text,
                title="📝 Write Lines",
                border_style="blue",
                title_align="center",
                padding=(1, 1),
                width=60
            ))

            console.print(
                "[bold blue]Write these lines?[/bold blue] ", end="")
            console.print("[dim](y/n)[/dim]: ", end="")
            response = input().strip().lower()

        else:

            print("\n" + "="*60)
            print(f"📝 WRITE LINES: {file_name}")
            print(f"Path: {file_path}")
            print(f"Info: {operation_info}")
            print("⚠️ This action cannot be undone!")
            print("="*60)

            response = input("Write these lines? (y/n): ").strip().lower()

        if response in ['y', 'yes']:
            if RICH_AVAILABLE and console:
                console.print("[green]✓ Writing lines...[/green]")
            else:
                print("✓ Writing lines...")
            return True
        else:
            if RICH_AVAILABLE and console:
                console.print("[blue]❌ Cancelled[/blue]")
            else:
                print("❌ Cancelled")
            return False

    except Exception as e:
        logger.warning(f"Error in write lines permission request: {str(e)}")
        return False


def get_replace_lines_info_display(file_path: str, start_line: int, end_line: int, content: str) -> str:
    """Get formatted display information about lines to be replaced."""
    try:
        lines = len(content.splitlines())
        chars = len(content)
        return f"Replace lines {start_line}-{end_line}: {lines} lines"
    except Exception:
        return f"Replace lines {start_line}-{end_line}: Unknown content"


def request_replace_lines_permission(file_path: str, start_line: int, end_line: int, content: str) -> bool:
    """Request user permission to replace lines with detailed information."""
    path = Path(file_path).resolve()
    file_name = path.name
    operation_info = get_replace_lines_info_display(
        file_path, start_line, end_line, content)

    try:
        if RICH_AVAILABLE and console:

            permission_text = Text()
            permission_text.append(
                f"File_name: {file_name}\n", style="bold yellow")

            display_path = file_path if len(
                file_path) <= 45 else "..." + file_path[-42:]
            permission_text.append(
                f"File_path: {display_path}\n", style="dim white")
            display_info = operation_info if len(
                operation_info) <= 45 else operation_info[:42] + "..."
            permission_text.append(f"\n{display_info}", style="dim cyan")
            permission_text.append(
                "\nThis action cannot be undone!", style="dim red")

            console.print(Panel(
                permission_text,
                title="🔄 Replace Lines",
                border_style="yellow",
                title_align="center",
                padding=(1, 1),
                width=60
            ))

            console.print(
                "[bold yellow]Replace these lines?[/bold yellow] ", end="")
            console.print("[dim](y/n)[/dim]: ", end="")
            response = input().strip().lower()

        else:

            print("\n" + "="*60)
            print(f"🔄 REPLACE LINES: {file_name}")
            print(f"Path: {file_path}")
            print(f"Info: {operation_info}")
            print("⚠️ This action cannot be undone!")
            print("="*60)

            response = input("Replace these lines? (y/n): ").strip().lower()

        if response in ['y', 'yes']:
            if RICH_AVAILABLE and console:
                console.print("[green]✓ Replacing lines...[/green]")
            else:
                print("✓ Replacing lines...")
            return True
        else:
            if RICH_AVAILABLE and console:
                console.print("[blue]❌ Cancelled[/blue]")
            else:
                print("❌ Cancelled")
            return False

    except Exception as e:
        logger.warning(f"Error in replace lines permission request: {str(e)}")
        return False


def get_delete_lines_info_display(file_path: str, start_line: int, end_line: int) -> str:
    """Get formatted display information about lines to be deleted."""
    try:
        lines_count = end_line - start_line + 1
        return f"Delete {lines_count} lines ({start_line}-{end_line})"
    except Exception:
        return f"Delete lines {start_line}-{end_line}"


def request_delete_lines_permission(file_path: str, start_line: int, end_line: int) -> bool:
    """Request user permission to delete lines with detailed information."""
    path = Path(file_path).resolve()
    file_name = path.name
    operation_info = get_delete_lines_info_display(
        file_path, start_line, end_line)

    try:
        if RICH_AVAILABLE and console:

            permission_text = Text()
            permission_text.append(
                f"File_name: {file_name}\n", style="bold red")

            display_path = file_path if len(
                file_path) <= 45 else "..." + file_path[-42:]
            permission_text.append(
                f"File_path: {display_path}\n", style="dim white")
            display_info = operation_info if len(
                operation_info) <= 45 else operation_info[:42] + "..."
            permission_text.append(f"\n{display_info}", style="dim cyan")
            permission_text.append(
                "\nThis action cannot be undone!", style="dim red")

            console.print(Panel(
                permission_text,
                title="🗑️ Delete Lines",
                border_style="red",
                title_align="center",
                padding=(1, 1),
                width=50
            ))

            console.print(
                "[bold red]Delete these lines?[/bold red] ", end="")
            console.print("[dim](y/n)[/dim]: ", end="")
            response = input().strip().lower()

        else:

            print("\n" + "="*50)
            print(f"🗑️ DELETE LINES: {file_name}")
            print(f"Path: {file_path}")
            print(f"Info: {operation_info}")
            print("⚠️ This action cannot be undone!")
            print("="*50)

            response = input("Delete these lines? (y/n): ").strip().lower()

        if response in ['y', 'yes']:
            if RICH_AVAILABLE and console:
                console.print("[green]✓ Deleting lines...[/green]")
            else:
                print("✓ Deleting lines...")
            return True
        else:
            if RICH_AVAILABLE and console:
                console.print("[blue]❌ Cancelled[/blue]")
            else:
                print("❌ Cancelled")
            return False

    except Exception as e:
        logger.warning(f"Error in delete lines permission request: {str(e)}")
        return False


def is_likely_text_file(file_path: Path) -> bool:
    """Checks if a file is likely text-based."""
    try:
        with open(file_path, 'rb') as f:
            chunk = f.read(1024)
            if b'\x00' in chunk:
                return False
    except IOError:
        return False
    return True


def write_lines(
    file_path: str,
    line_number: int,
    content: str
) -> tuple[bool, str]:
    """
    Insert new content at a specific line number in a text file.

    Args:
        file_path: Path to the file to edit
        line_number: Line number where to insert content (1-indexed)
        content: Content to insert

    Returns:
        (success, message)
    """
    try:
        log_function_call("write_lines", {
            'file_path': file_path,
            'line_number': line_number,
            'content_length': len(content)
        }, logger)

        p = Path(file_path)
        if not p.is_file():
            log_error(
                Exception(f"File not found: {file_path}"), "File not found", logger)
            return False, f"File not found at '{file_path}'\n📊 Tool call parameters: file_path='{file_path}', line_number={line_number}, content={content}"

        if not is_likely_text_file(p):
            log_error(
                Exception(f"Binary file: {file_path}"), "Binary file cannot be edited", logger)
            return False, f"File '{p.name}' appears to be a binary file.\n📊 Tool call parameters: file_path='{file_path}', line_number={line_number}, content={content}"

        if line_number < 1:
            log_error(Exception("Invalid line number"),
                      "Line number must be >= 1", logger)
            return False, f"Line numbers must be 1 or greater.\n📊 Tool call parameters: file_path='{file_path}', line_number={line_number}, content={content}"

        try:
            from vcs.backup_manager import BackupManager
            backup_mgr = BackupManager()
            backup_mgr.backup_file(file_path)
        except Exception:
            pass

        if not request_write_lines_permission(file_path, line_number, content):
            return False, f"""❌ Line insertion cancelled by user. This suggests one of several possibilities:

            • The insertion location might not be appropriate for the content
            • The content being inserted may need modification or reorganization
            • There might be logical flow issues with the current insertion point
            • The insertion could create redundancy or disrupt existing functionality

            Let's reconsider the approach:
            1. Is this the correct location to insert the new content?
            2. Does the content fit naturally with the existing code flow?
            3. Should we modify the content or find a different insertion approach?
            4. Would replacing existing content be more appropriate than insertion?

            Let's think about this differently and find an editing approach that works better."""

        try:
            with open(p, 'r', encoding='utf-8', errors='ignore') as f:
                all_lines = f.readlines()
        except IOError as e:
            log_error(e, f"Could not read file: {file_path}", logger)
            return False, f"Could not read file: {e}\n📊 Tool call parameters: file_path='{file_path}'"

        total_lines = len(all_lines)
        start_index = line_number - 1

        if start_index > total_lines:
            return False, f"Line number {line_number} is out of bounds. File has {total_lines} lines.\n📊 Tool call parameters: file_path='{file_path}', line_number={line_number}, content={repr(content)}"

        indentation = ""
        if start_index < total_lines:
            indentation = all_lines[start_index][:len(
                all_lines[start_index]) - len(all_lines[start_index].lstrip())]
        elif total_lines > 0:
            indentation = all_lines[-1][:len(all_lines[-1]) -
                                        len(all_lines[-1].lstrip())]

        content_lines = [
            f"{indentation}{line}\n" for line in content.splitlines()]
        all_lines[start_index:start_index] = content_lines

        temp_file_path = p.with_suffix(f"{p.suffix}.tmp")
        try:
            with open(temp_file_path, 'w', encoding='utf-8') as f:
                f.writelines(all_lines)
            os.replace(temp_file_path, p)
            log_success(
                f"Successfully inserted content at line {line_number} in {p.name}", logger)
            return True, f"Successfully inserted content at line {line_number} in '{p.name}'.\n📊 Tool call parameters: file_path='{file_path}', line_number={line_number}, content={repr(content)}"
        except IOError as e:
            log_error(
                e, f"Failed to write changes to file: {file_path}", logger)
            return False, f"Failed to write changes to file: {e}\n📊 Tool call parameters: file_path='{file_path}', line_number={line_number}, content={content}"
        finally:
            if temp_file_path.exists():
                os.remove(temp_file_path)

    except Exception as e:
        log_error(e, f"Error in write_lines for {file_path}", logger)
        return False, f"Error inserting content: {str(e)}\n📊 Tool call parameters: file_path='{file_path}', line_number={line_number}, content={content}"


def replace_lines(
    file_path: str,
    start_line: int,
    end_line: int,
    content: str
) -> tuple[bool, str]:
    """
    Replace a range of lines with new content in a text file.

    Args:
        file_path: Path to the file to edit
        start_line: Starting line number (1-indexed, inclusive)
        end_line: Ending line number (1-indexed, inclusive)
        content: Content to replace the lines with

    Returns:
        (success, message)
    """
    try:
        log_function_call("replace_lines", {
            'file_path': file_path,
            'start_line': start_line,
            'end_line': end_line,
            'content_length': len(content)
        }, logger)

        p = Path(file_path)
        if not p.is_file():
            log_error(
                Exception(f"File not found: {file_path}"), "File not found", logger)
            return False, f"File not found at '{file_path}'\n📊 Tool call parameters: file_path='{file_path}', start_line={start_line}, end_line={end_line}, content={content}"

        if not is_likely_text_file(p):
            log_error(
                Exception(f"Binary file: {file_path}"), "Binary file cannot be edited", logger)
            return False, f"File '{p.name}' appears to be a binary file.\n📊 Tool call parameters: file_path='{file_path}', start_line={start_line}, end_line={end_line}, content={content}"

        if start_line < 1 or end_line < start_line:
            log_error(Exception("Invalid line range"),
                      "Invalid line range", logger)
            return False, f"Start line must be >= 1 and end line must be >= start line.\n📊 Tool call parameters: file_path='{file_path}', start_line={start_line}, end_line={end_line}, content={repr(content)}"

        try:
            from vcs.backup_manager import BackupManager
            backup_mgr = BackupManager()
            backup_mgr.backup_file(file_path)
        except Exception:
            pass

        if not request_replace_lines_permission(file_path, start_line, end_line, content):
            return False, f"""❌ Line replacement cancelled by user. This suggests one of several possibilities:

            • The replacement content might not be what user intended
            • The scope of replacement (lines {start_line}-{end_line}) might be too broad or narrow
            • There could be important content in the lines being replaced
            • The replacement might break existing functionality or logic

            Let's reconsider the approach:
            1. Are we replacing the correct lines with the right content?
            2. Should we use a more targeted replacement or insertion instead?
            3. Is there important context we're overlooking in the replacement?
            4. Would modifying the content or approach yield better results?

            Let's think about this differently and find a replacement strategy that works better."""

        try:
            with open(p, 'r', encoding='utf-8', errors='ignore') as f:
                all_lines = f.readlines()
        except IOError as e:
            log_error(e, f"Could not read file: {file_path}", logger)
            return False, f"Could not read file: {e}\n📊 Tool call parameters: file_path='{file_path}', start_line={start_line}, end_line={end_line}, content={repr(content)}"

        total_lines = len(all_lines)
        start_index = start_line - 1
        end_index = end_line

        if start_index >= total_lines:
            return False, f"Start line {start_line} is out of bounds. File has {total_lines} lines.\n📊 Tool call parameters: file_path='{file_path}', start_line={start_line}, end_line={end_line}, content={repr(content)}"

        if end_index > total_lines:
            end_index = total_lines

        indentation = ""
        if start_index < total_lines:
            indentation = all_lines[start_index][:len(
                all_lines[start_index]) - len(all_lines[start_index].lstrip())]

        content_lines = [
            f"{indentation}{line}\n" for line in content.splitlines()]
        all_lines[start_index:end_index] = content_lines

        temp_file_path = p.with_suffix(f"{p.suffix}.tmp")
        try:
            with open(temp_file_path, 'w', encoding='utf-8') as f:
                f.writelines(all_lines)
            os.replace(temp_file_path, p)
            log_success(
                f"Successfully replaced lines {start_line}-{end_line} in {p.name}", logger)
            return True, f"Successfully replaced lines {start_line}-{end_line} in '{p.name}'.\n📊 Tool call parameters: file_path='{file_path}', start_line={start_line}, end_line={end_line}, content={repr(content)}"
        except IOError as e:
            log_error(
                e, f"Failed to write changes to file: {file_path}", logger)
            return False, f"Failed to write changes to file: {e}\n📊 Tool call parameters: file_path='{file_path}', start_line={start_line}, end_line={end_line}, content={repr(content)}"
        finally:
            if temp_file_path.exists():
                os.remove(temp_file_path)

    except Exception as e:
        log_error(e, f"Error in replace_lines for {file_path}", logger)
        return False, f"Error replacing lines: {str(e)}\n📊 Tool call parameters: file_path='{file_path}', start_line={start_line}, end_line={end_line}, content={repr(content)}"


def delete_lines(
    file_path: str,
    start_line: int,
    end_line: int
) -> tuple[bool, str]:
    """
    Delete a range of lines from a text file.

    Args:
        file_path: Path to the file to edit
        start_line: Starting line number (1-indexed, inclusive)
        end_line: Ending line number (1-indexed, inclusive)

    Returns:
        (success, message)
    """
    try:
        log_function_call("delete_lines", {
            'file_path': file_path,
            'start_line': start_line,
            'end_line': end_line
        }, logger)

        p = Path(file_path)
        if not p.is_file():
            log_error(
                Exception(f"File not found: {file_path}"), "File not found", logger)
            return False, f"File not found at '{file_path}'\n📊 Tool call parameters: file_path='{file_path}', start_line={start_line}, end_line={end_line}"

        if not is_likely_text_file(p):
            log_error(
                Exception(f"Binary file: {file_path}"), "Binary file cannot be edited", logger)
            return False, f"File '{p.name}' appears to be a binary file.\n📊 Tool call parameters: file_path='{file_path}', start_line={start_line}, end_line={end_line}"

        if start_line < 1 or end_line < start_line:
            log_error(Exception("Invalid line range"),
                      "Invalid line range", logger)
            return False, f"Start line must be >= 1 and end line must be >= start line.\n📊 Tool call parameters: file_path='{file_path}', start_line={start_line}, end_line={end_line}"

        try:
            from vcs.backup_manager import BackupManager
            backup_mgr = BackupManager()
            backup_mgr.backup_file(file_path)
        except Exception:
            pass

        if not request_delete_lines_permission(file_path, start_line, end_line):
            return False, f"""❌ Line deletion cancelled by user. This suggests one of several possibilities:

            • The lines being deleted (lines {start_line}-{end_line}) might contain important content
            • There could be dependencies or references that would break with deletion
            • The deletion scope might be too broad and could remove necessary code
            • The lines might be part of a larger logical block that shouldn't be disrupted

            Let's reconsider the approach:
            1. Are we deleting the correct lines, or should we be more selective?
            2. Is there important functionality or data in these lines?
            3. Should we comment out the lines instead of deleting them?
            4. Would replacing the content be a better approach than deletion?

            Let's think about this differently and find a safer approach to code modification."""

        try:
            with open(p, 'r', encoding='utf-8', errors='ignore') as f:
                all_lines = f.readlines()
        except IOError as e:
            log_error(e, f"Could not read file: {file_path}", logger)
            return False, f"Could not read file: {e}\n📊 Tool call parameters: file_path='{file_path}', start_line={start_line}, end_line={end_line}"

        total_lines = len(all_lines)
        start_index = start_line - 1
        end_index = end_line

        if start_index >= total_lines:
            return False, f"Start line {start_line} is out of bounds. File has {total_lines} lines.\n📊 Tool call parameters: file_path='{file_path}', start_line={start_line}, end_line={end_line}"

        if end_index > total_lines:
            end_index = total_lines

        deleted_lines = all_lines[start_index:end_index]
        del all_lines[start_index:end_index]

        temp_file_path = p.with_suffix(f"{p.suffix}.tmp")
        try:
            with open(temp_file_path, 'w', encoding='utf-8') as f:
                f.writelines(all_lines)
            os.replace(temp_file_path, p)
            log_success(
                f"Successfully deleted lines {start_line}-{end_line} from {p.name}", logger)
            return True, f"Successfully deleted {len(deleted_lines)} lines ({start_line}-{end_line}) from '{p.name}'.\n📊 Tool call parameters: file_path='{file_path}', start_line={start_line}, end_line={end_line}"
        except IOError as e:
            log_error(
                e, f"Failed to write changes to file: {file_path}", logger)
            return False, f"Failed to write changes to file: {e}\n📊 Tool call parameters: file_path='{file_path}', start_line={start_line}, end_line={end_line}"
        finally:
            if temp_file_path.exists():
                os.remove(temp_file_path)

    except Exception as e:
        log_error(e, f"Error in delete_lines for {file_path}", logger)
        return False, f"Error deleting lines: {str(e)}\n📊 Tool call parameters: file_path='{file_path}', start_line={start_line}, end_line={end_line}"
