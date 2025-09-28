#!/usr/bin/env python3
import shutil
from pathlib import Path
from util.logging import get_logger, log_function_call, log_error, log_success

logger = get_logger("delete")

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    RICH_AVAILABLE = True
    console = Console()
except ImportError:
    RICH_AVAILABLE = False


def get_file_info_display(file_path: str) -> str:
    """Get formatted display information about a file for deletion confirmation."""
    path = Path(file_path).resolve()
    try:
        size = path.stat().st_size

        if size < 1024:
            size_str = f"{size} bytes"
        elif size < 1024 * 1024:
            size_str = f"{size / 1024:.1f} KB"
        else:
            size_str = f"{size / (1024 * 1024):.1f} MB"

        return f"Size: {size_str}"
    except Exception:
        return "Size: Unknown"


def get_folder_info_display(folder_path: str, recursive: bool = False) -> str:
    """Get formatted display information about a folder for deletion confirmation."""
    path = Path(folder_path).resolve()
    try:
        if recursive:

            total_files = sum(1 for _ in path.rglob('*') if _.is_file())
            total_folders_raw = sum(1 for _ in path.rglob('*') if _.is_dir())
            total_folders = max(0, total_folders_raw - 1)
            total_size = sum(
                _.stat().st_size for _ in path.rglob('*') if _.is_file())

            if total_size < 1024:
                size_str = f"{total_size} bytes"
            elif total_size < 1024 * 1024:
                size_str = f"{total_size / 1024:.1f} KB"
            else:
                size_str = f"{total_size / (1024 * 1024):.1f} MB"

            if total_folders == 0:
                return f"{total_files} files"
            else:
                return f"{total_files} files, {total_folders} folders"
        else:

            items = list(path.iterdir())
            file_count = sum(1 for item in items if item.is_file())
            folder_count = sum(1 for item in items if item.is_dir())

            if not items:
                return "Empty folder"
            elif folder_count == 0:
                return f"{file_count} files"
            else:
                return f"{file_count} files, {folder_count} folders"
    except Exception:
        return "Unable to determine"


def request_file_deletion_permission(file_path: str) -> bool:
    """Request user permission to delete a file with detailed information."""
    path = Path(file_path).resolve()
    file_name = path.name
    file_info = get_file_info_display(file_path)

    try:
        if RICH_AVAILABLE and console:

            permission_text = Text()
            permission_text.append(
                f"File_name: {file_name}\n", style="bold yellow")

            display_path = file_path if len(
                file_path) <= 45 else "..." + file_path[-42:]
            permission_text.append(
                f"File_path: {display_path}\n", style="dim white")
            permission_text.append(
                "\nThis action cannot be undone!", style="dim red")

            console.print(Panel(
                permission_text,
                title="🗑️  Delete File",
                border_style="red",
                title_align="center",
                padding=(1, 1),
                width=50
            ))

            console.print(
                "[bold yellow]Delete this file?[/bold yellow] ", end="")
            console.print("[dim](y/n)[/dim]: ", end="")
            response = input().strip().lower()

        else:

            print("\n" + "="*50)
            print(f"🗑️  DELETE FILE: {file_name}")
            print(f"Path: {file_path}")
            print("⚠️ This action cannot be undone!")
            print("="*50)

            response = input("Delete this file? (y/n): ").strip().lower()

        if response in ['y', 'yes']:
            if RICH_AVAILABLE and console:
                console.print("[green]✓ Deleting file...[/green]")
            else:
                print("✓ Deleting file...")
            return True
        else:
            if RICH_AVAILABLE and console:
                console.print("[blue]❌ Cancelled[/blue]")
            else:
                print("❌ Cancelled")
            return False

    except Exception as e:
        logger.warning(f"Error in file deletion permission request: {str(e)}")
        return False


def request_folder_deletion_permission(folder_path: str, recursive: bool = False) -> bool:
    """Request user permission to delete a folder with detailed information."""
    path = Path(folder_path).resolve()
    folder_name = path.name
    folder_info = get_folder_info_display(folder_path, recursive)

    deletion_type = "RECURSIVE" if recursive else "EMPTY"
    warning_msg = "This will permanently delete the folder AND ALL ITS CONTENTS!" if recursive else "This will delete the empty folder."

    try:
        if RICH_AVAILABLE and console:
            permission_text = Text()
            permission_text.append(
                f"Folder_name: {folder_name}/\n", style="bold yellow")
            display_path = folder_path if len(
                folder_path) <= 45 else "..." + folder_path[-42:]
            permission_text.append(
                f"Folder_path: {display_path}\n", style="dim white")
            display_info = folder_info if len(
                folder_info) <= 45 else folder_info[:42] + "..."
            permission_text.append(f"\n{display_info}", style="dim cyan")
            permission_text.append(
                "\nThis action cannot be undone!", style="dim red")

            console.print(Panel(
                permission_text,
                title=f"🗂️  Delete {deletion_type} Folder",
                border_style="red",
                title_align="center",
                padding=(1, 1),
                width=60
            ))

            console.print(
                "[bold yellow]Delete this folder?[/bold yellow] ", end="")
            console.print("[dim](y/n)[/dim]: ", end="")
            response = input().strip().lower()

        else:

            print("\n" + "="*60)
            print(f"🗂️ DELETE {deletion_type} FOLDER: {folder_name}/")
            print(f"Path: {folder_path}")
            print(f"Info: {folder_info}")
            print("⚠️ This action cannot be undone!")
            print("="*60)

            response = input("Delete this folder? (y/n): ").strip().lower()

        if response in ['y', 'yes']:
            if RICH_AVAILABLE and console:
                console.print("[green]✓ Deleting folder...[/green]")
            else:
                print("✓ Deleting folder...")
            return True
        else:
            if RICH_AVAILABLE and console:
                console.print("[blue]❌ Cancelled[/blue]")
            else:
                print("❌ Cancelled")
            return False

    except Exception as e:
        logger.warning(
            f"Error in folder deletion permission request: {str(e)}")
        return False


def delete_file(file_path: str) -> tuple[bool, str]:
    """
    Delete a file with user permission and error handling.

    Args:
        file_path: Path to the file to delete

    Returns:
        (success, message)
    """
    try:
        log_function_call("delete_file", {
            'file_path': file_path
        }, logger)

        path = Path(file_path).resolve()

        if not path.exists():
            log_error(
                Exception(f"File not found: {file_path}"), "File not found", logger)
            return False, f"File not found: {file_path}\n📊 Tool call parameters: file_path='{file_path}'"

        if not path.is_file():
            log_error(
                Exception(f"Path is not a file: {file_path}"), "Path is not a file", logger)
            return False, f"{file_path} is not a file\n📊 Tool call parameters: file_path='{file_path}'"

        if not request_file_deletion_permission(file_path):
            return False, f"""❌ File deletion cancelled by user. This suggests one of several possibilities:

            • The file might contain important data or configuration that should be preserved
            • There could be dependencies or references to this file elsewhere in the project
            • The file might be part of a larger system that would break without it
            • There might be backup or version control considerations

            Let's reconsider the approach:
            1. Is this file truly no longer needed, or should we archive it instead?
            2. Are there any references to this file that would break if deleted?
            3. Should we create a backup before deletion?
            4. Would moving the file to a different location be more appropriate?

            Let's think about this differently and find a safer approach to file management."""

        try:
            from vcs.backup_manager import BackupManager
            backup_mgr = BackupManager()
            backup_mgr.backup_deleted_file(str(path))
        except Exception:
            pass

        try:
            path.unlink()
            log_success(f"Successfully deleted file: {file_path}", logger)
            return True, f"Successfully deleted file: {file_path}\n📊 Tool call parameters: file_path='{file_path}'"
        except PermissionError as e:
            log_error(
                e, f"Permission denied deleting file {file_path}", logger)
            return False, f"Permission denied when attempting to delete {file_path}\n📊 Tool call parameters: file_path='{file_path}'"
        except Exception as e:
            log_error(e, f"Failed to delete file {file_path}", logger)
            return False, f"Failed to delete file {file_path}: {str(e)}\n📊 Tool call parameters: file_path='{file_path}'"

    except Exception as e:
        log_error(e, f"Unexpected error deleting file {file_path}", logger)
        return False, f"Unexpected error deleting file {file_path}: {str(e)}\n📊 Tool call parameters: file_path='{file_path}'"


def delete_folder(folder_path: str, recursive: bool = False) -> tuple[bool, str]:
    """
    Delete a folder with user permission and error handling.

    Args:
        folder_path: Path to the folder to delete
        recursive: Whether to delete non-empty directories

    Returns:
        (success, message)
    """
    try:
        log_function_call("delete_folder", {
            'folder_path': folder_path,
            'recursive': recursive
        }, logger)

        path = Path(folder_path).resolve()

        if not path.exists():
            log_error(
                Exception(f"Folder not found: {folder_path}"), "Folder not found", logger)
            return False, f"Folder not found: {folder_path}\n📊 Tool call parameters: folder_path='{folder_path}', recursive={recursive}"

        if not path.is_dir():
            log_error(Exception(
                f"Path is not a directory: {folder_path}"), "Path is not a directory", logger)
            return False, f"{folder_path} is not a directory\n📊 Tool call parameters: folder_path='{folder_path}', recursive={recursive}"

        if not recursive and any(path.iterdir()):
            log_error(Exception(
                f"Directory not empty: {folder_path}"), "Directory not empty", logger)
            return False, f"Directory {folder_path} is not empty. Use recursive=True to delete non-empty directories.\n📊 Tool call parameters: folder_path='{folder_path}', recursive={recursive}"

        if not request_folder_deletion_permission(folder_path, recursive):
            deletion_type = "RECURSIVE" if recursive else "REGULAR"
            return False, f"""❌ {deletion_type} folder deletion cancelled by user. This suggests one of several possibilities:

            • The folder might contain important files, subdirectories, or configuration data
            • There could be project dependencies or references that rely on this folder structure
            • The folder might be part of a larger system architecture that would be disrupted
            • There might be organizational or backup considerations for the folder contents

            Let's reconsider the approach:
            1. Are all files/subfolders in this directory truly no longer needed?
            2. Are there any project references or dependencies on this folder structure?
            3. Should we archive or backup the folder contents before deletion?
            4. Would reorganizing the folder structure be more appropriate than deletion?

            Let's think about this differently and find a safer approach to directory management."""

        if recursive:
            try:
                from vcs.backup_manager import BackupManager
                backup_mgr = BackupManager()
                for file_path in path.rglob('*'):
                    if file_path.is_file():
                        backup_mgr.backup_deleted_file(str(file_path))
            except Exception:
                pass

        try:
            if recursive:
                shutil.rmtree(path)
                log_success(
                    f"Successfully deleted directory and all contents: {folder_path}", logger)
                return True, f"Successfully deleted directory and all its contents: {folder_path}\n📊 Tool call parameters: folder_path='{folder_path}', recursive={recursive}"
            else:
                path.rmdir()
                log_success(
                    f"Successfully deleted empty directory: {folder_path}", logger)
                return True, f"Successfully deleted empty directory: {folder_path}\n📊 Tool call parameters: folder_path='{folder_path}', recursive={recursive}"
        except PermissionError as e:
            log_error(
                e, f"Permission denied deleting directory {folder_path}", logger)
            return False, f"Permission denied when attempting to delete {folder_path}\n📊 Tool call parameters: folder_path='{folder_path}', recursive={recursive}"
        except Exception as e:
            log_error(e, f"Failed to delete directory {folder_path}", logger)
            return False, f"Failed to delete directory {folder_path}: {str(e)}\n📊 Tool call parameters: folder_path='{folder_path}', recursive={recursive}"

    except Exception as e:
        log_error(
            e, f"Unexpected error deleting directory {folder_path}", logger)
        return False, f"Unexpected error deleting directory {folder_path}: {str(e)}\n📊 Tool call parameters: folder_path='{folder_path}', recursive={recursive}"
