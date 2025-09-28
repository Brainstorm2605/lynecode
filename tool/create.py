#!/usr/bin/env python3
from pathlib import Path
from util.logging import get_logger, log_function_call, log_error, log_success

logger = get_logger("create")

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    RICH_AVAILABLE = True
    console = Console()
except ImportError:
    RICH_AVAILABLE = False


def get_file_creation_info_display(file_path: str, content: str = "") -> str:
    """Get formatted display information about a file to be created."""
    path = Path(file_path).resolve()
    try:
        if content:
            lines = len(content.splitlines())
            chars = len(content)
            return f"Content: {lines} lines, {chars} characters"
        else:
            return "Content: Empty file"
    except Exception:
        return "Content: Unknown"


def request_file_creation_permission(file_path: str, content: str = "") -> bool:
    """Request user permission to create a file with detailed information."""
    path = Path(file_path).resolve()
    file_name = path.name
    file_info = get_file_creation_info_display(file_path, content)

    try:
        if RICH_AVAILABLE and console:

            permission_text = Text()
            permission_text.append(
                f"File_name: {file_name}\n", style="bold green")

            display_path = file_path if len(
                file_path) <= 45 else "..." + file_path[-42:]
            permission_text.append(
                f"File_path: {display_path}\n", style="dim white")
            display_info = file_info if len(
                file_info) <= 45 else file_info[:42] + "..."
            permission_text.append(f"\n{display_info}", style="dim cyan")

            console.print(Panel(
                permission_text,
                title="📄 Create File",
                border_style="green",
                title_align="center",
                padding=(1, 1),
                width=50
            ))

            console.print(
                "[bold green]Create this file?[/bold green] ", end="")
            console.print("[dim](y/n)[/dim]: ", end="")
            response = input().strip().lower()

        else:

            print("\n" + "="*50)
            print(f"📄 CREATE FILE: {file_name}")
            print(f"Path: {file_path}")
            print(f"Info: {file_info}")
            print("="*50)

            response = input("Create this file? (y/n): ").strip().lower()

        if response in ['y', 'yes']:
            if RICH_AVAILABLE and console:
                console.print("[green]✓ Creating file...[/green]")
            else:
                print("✓ Creating file...")
            return True
        else:
            if RICH_AVAILABLE and console:
                console.print("[blue]❌ Cancelled[/blue]")
            else:
                print("❌ Cancelled")
            return False

    except Exception as e:
        logger.warning(f"Error in file creation permission request: {str(e)}")
        return False


def get_folder_creation_info_display(folder_path: str) -> str:
    """Get formatted display information about a folder to be created."""
    path = Path(folder_path).resolve()
    try:
        parent_exists = path.parent.exists()
        if parent_exists:
            return "Parent directory exists"
        else:
            return "Will create parent directories"
    except Exception:
        return "Unknown"


def request_folder_creation_permission(folder_path: str) -> bool:
    """Request user permission to create a folder with detailed information."""
    path = Path(folder_path).resolve()
    folder_name = path.name
    folder_info = get_folder_creation_info_display(folder_path)

    try:
        if RICH_AVAILABLE and console:

            permission_text = Text()
            permission_text.append(
                f"Folder_name: {folder_name}/\n", style="bold green")

            display_path = folder_path if len(
                folder_path) <= 45 else "..." + folder_path[-42:]
            permission_text.append(
                f"Folder_path: {display_path}\n", style="dim white")
            display_info = folder_info if len(
                folder_info) <= 45 else folder_info[:42] + "..."
            permission_text.append(f"\n{display_info}", style="dim cyan")

            console.print(Panel(
                permission_text,
                title="📁 Create Folder",
                border_style="green",
                title_align="center",
                padding=(1, 1),
                width=50
            ))

            console.print(
                "[bold green]Create this folder?[/bold green] ", end="")
            console.print("[dim](y/n)[/dim]: ", end="")
            response = input().strip().lower()

        else:

            print("\n" + "="*50)
            print(f"📁 CREATE FOLDER: {folder_name}/")
            print(f"Path: {folder_path}")
            print(f"Info: {folder_info}")
            print("="*50)

            response = input("Create this folder? (y/n): ").strip().lower()

        if response in ['y', 'yes']:
            if RICH_AVAILABLE and console:
                console.print("[green]✓ Creating folder...[/green]")
            else:
                print("✓ Creating folder...")
            return True
        else:
            if RICH_AVAILABLE and console:
                console.print("[blue]❌ Cancelled[/blue]")
            else:
                print("❌ Cancelled")
            return False

    except Exception as e:
        logger.warning(
            f"Error in folder creation permission request: {str(e)}")
        return False


def create_file(file_path: str, content: str = "") -> tuple[bool, str]:
    """
    Create a new file with optional content.

    Args:
        file_path: Path to the file to create
        content: Content to write to the file

    Returns:
        (success, message)
    """
    try:
        log_function_call("create_file", {
            'file_path': file_path,
            'content_length': len(content)
        }, logger)

        path = Path(file_path).resolve()

        if path.exists():
            if not path.is_file():
                log_error(Exception(
                    f"Path exists but not a file: {file_path}"), "Path is not a file", logger)
                content_info = repr(content) if content else "'' (empty file)"
                return False, f"Path exists but is not a file: {file_path}\n📊 Tool call parameters: file_path='{file_path}', content={content_info}"
            else:
                log_error(
                    Exception(f"File already exists: {file_path}"), "File already exists", logger)
                content_info = repr(content) if content else "'' (empty file)"
                return False, f"File already exists: {file_path}\n📊 Tool call parameters: file_path='{file_path}', content={content_info}"

        if not request_file_creation_permission(file_path, content):
            return False, f"""❌ File creation cancelled by user. This suggests one of several possibilities:

            • The file location or name might not be what user wanted
            • The content may need modification before creation
            • There might be naming conflicts or permission issues
            • The file structure might need to be reconsidered

            Let's reconsider the approach:
            1. Is this the correct location for the new file?
            2. Does the file name accurately reflect its purpose?
            3. Should we modify the content before creating the file?
            4. Is there a different file structure that would work better?

            Let's think about this differently and find a solution that works best for user needs"""

        try:
            path.parent.mkdir(parents=True, exist_ok=True)
        except PermissionError as e:
            log_error(
                e, f"Permission denied creating parent directory for {file_path}", logger)
            content_info = repr(content) if content else "'' (empty file)"
            return False, f"Permission denied when creating parent directory for {file_path}\n📊 Tool call parameters: file_path='{file_path}', content={content_info}"
        except Exception as e:
            log_error(
                e, f"Failed to create parent directory for {file_path}", logger)
            content_info = repr(content) if content else "'' (empty file)"
            return False, f"Failed to create parent directory for {file_path}: {str(e)}\n📊 Tool call parameters: file_path='{file_path}', content={content_info}"

        try:

            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)

            log_success(f"Successfully created file: {file_path}", logger)
            content_info = repr(content) if content else "'' (empty file)"
            return True, f"Successfully created file: {file_path}\n📊 Tool call parameters: file_path='{file_path}', content={content_info}"
        except PermissionError as e:
            log_error(
                e, f"Permission denied creating file {file_path}", logger)
            content_info = repr(content) if content else "'' (empty file)"
            return False, f"Permission denied when creating file {file_path}\n📊 Tool call parameters: file_path='{file_path}', content={content_info}"
        except Exception as e:
            log_error(e, f"Failed to create file {file_path}", logger)
            content_info = repr(content) if content else "'' (empty file)"
            return False, f"Failed to create file {file_path}: {str(e)}\n📊 Tool call parameters: file_path='{file_path}', content={content_info}"

    except Exception as e:
        log_error(e, f"Unexpected error creating file {file_path}", logger)
        content_info = repr(content) if content else "'' (empty file)"
        return False, f"Unexpected error creating file {file_path}: {str(e)}\n📊 Tool call parameters: file_path='{file_path}', content={content_info}"


def create_folder(folder_path: str) -> tuple[bool, str]:
    """
    Create a new directory.

    Args:
        folder_path: Path to the directory to create

    Returns:
        (success, message)
    """
    try:
        log_function_call("create_folder", {
            'folder_path': folder_path
        }, logger)

        path = Path(folder_path).resolve()

        if path.exists():
            if path.is_dir():
                log_error(Exception(
                    f"Directory already exists: {folder_path}"), "Directory already exists", logger)
                return False, f"Directory already exists: {folder_path}\n📊 Tool call parameters: folder_path='{folder_path}'"
            else:
                log_error(Exception(
                    f"Path exists but not a directory: {folder_path}"), "Path is not a directory", logger)
                return False, f"{folder_path} exists but is not a directory\n📊 Tool call parameters: folder_path='{folder_path}'"

        if not request_folder_creation_permission(folder_path):
            return False, f"""❌ Folder creation cancelled by user. This suggests one of several possibilities:

            • The folder location or naming might not align with user project structure
            • There might be organizational issues with the directory hierarchy
            • Permission constraints could be affecting folder creation
            • The folder purpose might need clarification

            Let's reconsider the approach:
            1. Is this the right location in user project structure?
            2. Does the folder name clearly indicate its purpose?
            3. Should we create intermediate folders or reconsider the structure?
            4. Is there a better way to organize this content?

            Let's think about this differently and find an organizational approach that works best for user needs."""

        try:
            path.mkdir(parents=True, exist_ok=True)
            log_success(
                f"Successfully created directory: {folder_path}", logger)
            return True, f"Successfully created directory: {folder_path}\n📊 Tool call parameters: folder_path='{folder_path}'"
        except PermissionError as e:
            log_error(
                e, f"Permission denied creating directory {folder_path}", logger)
            return False, f"Permission denied when creating directory {folder_path}\n📊 Tool call parameters: folder_path='{folder_path}'"
        except Exception as e:
            log_error(e, f"Failed to create directory {folder_path}", logger)
            return False, f"Failed to create directory {folder_path}: {str(e)}\n📊 Tool call parameters: folder_path='{folder_path}'"

    except Exception as e:
        log_error(
            e, f"Unexpected error creating directory {folder_path}", logger)
        return False, f"Unexpected error creating directory {folder_path}: {str(e)}\n📊 Tool call parameters: folder_path='{folder_path}'"
