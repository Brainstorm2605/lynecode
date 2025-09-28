#!/usr/bin/env python3
"""
Version Control System for Lyne

Main VCS module that provides menu-based version management.
"""

import os
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table

from .backup_manager import BackupManager
from .diff_viewer import DiffViewer
from util.logging import get_logger

logger = get_logger("version_control")


class VersionControl:
    """Main version control system with menu interface."""

    def __init__(self, project_path: str):
        """Initialize VCS with backup manager and diff viewer."""
        self.project_path = Path(project_path).resolve()
        self.backup_manager = BackupManager(str(self.project_path))
        self.diff_viewer = DiffViewer()
        self.console = Console()

    def show_main_menu(self) -> None:
        """Display the main VCS menu."""
        menu_text = Text()
        menu_text.append(
            "Choose a version control option:\n\n", style="bold cyan")

        menu_text.append(
            "○ 1. 📁  View & Restore File Versions\n", style="white")
        menu_text.append("○ 2. 🗂️  Recover Deleted Files\n", style="red")
        menu_text.append("○ 3. 📂  Browse Project Changes\n", style="white")
        menu_text.append("○ 4. 🔄  Undo Last File Change\n", style="white")
        menu_text.append("○ 5. 🧹  Clean Up Old Versions\n", style="white")
        menu_text.append("○ 6. ℹ️  View Backup Information\n", style="white")
        menu_text.append("○ 0. 🔙  Back to Navigation Menu\n", style="yellow")

        self.console.print(Panel(
            menu_text,
            title="🔄 FILE VERSION CONTROL",
            border_style="cyan",
            title_align="center",
            padding=(1, 2)
        ))

    def run_menu(self) -> bool:
        """
        Run the VCS menu system.

        Returns:
            True if user wants to continue, False to exit
        """
        while True:
            self.show_main_menu()

            try:
                choice = self.console.input(
                    "\n👤 [bold cyan]Select option (0-6):[/bold cyan] ").strip()

                if choice == "0":
                    return True

                elif choice == "1":
                    self._handle_file_browser()

                elif choice == "2":
                    self._handle_deleted_files()

                elif choice == "3":
                    self._handle_folder_browser()

                elif choice == "4":
                    self._handle_quick_revert()

                elif choice == "5":
                    self._handle_cleanup()

                elif choice == "6":
                    self._handle_statistics()

                else:
                    self.console.print(
                        "❌ [bold red]Please enter a number between 0 and 6.[/bold red]")

            except KeyboardInterrupt:
                self.console.print(
                    "\n\n👋 [bold yellow]Returning to navigation menu...[/bold yellow]")
                return True
            except Exception as e:
                self.console.print(f"❌ [bold red]Error: {str(e)}[/bold red]")
                return True

    def _handle_deleted_files(self) -> None:
        """Handle deleted files restoration menu."""
        deleted_files = self.backup_manager.get_deleted_files()

        if not deleted_files:
            self.console.print(Panel(
                "🗂️ No deleted files available for restoration.\n\n"
                "Deleted files are automatically backed up when you use the delete commands.\n"
                "Try deleting some files first to see them here.",
                title="📭 NO DELETED FILES",
                border_style="yellow",
                padding=(1, 2)
            ))
            return

        table = Table(show_header=True, header_style="bold red",
                      border_style="red")
        table.add_column("#", justify="right", style="white")
        table.add_column("File", style="white")
        table.add_column("Original Path", style="yellow")
        table.add_column("Deleted", style="red")
        table.add_column("Size", justify="right", style="cyan")

        for i, deleted_file in enumerate(deleted_files, 1):
            timestamp = datetime.fromtimestamp(
                float(deleted_file.get("deleted_at", 0)))
            readable_time = timestamp.strftime("%Y-%m-%d %H:%M")

            original_path = deleted_file.get("original_path", "")
            file_name = Path(
                original_path).name if original_path else "Unknown"

            size = deleted_file.get("size", 0)
            if size < 1024:
                size_str = f"{size}B"
            elif size < 1024 * 1024:
                size_str = f"{size // 1024}KB"
            else:
                size_str = f"{size // (1024 * 1024)}MB"

            table.add_row(str(i), file_name, original_path,
                          readable_time, size_str)

        self.console.print(Panel(
            table,
            title="🗂️   DELETED FILES (Available for Restoration)",
            border_style="red",
            padding=(1, 2)
        ))

        while True:
            try:
                max_choice = len(deleted_files)
                choice_str = self.console.input(
                    f"\n👤 [bold cyan]Select file to restore (1-{max_choice}) or 0 to cancel:[/bold cyan] ").strip()

                if choice_str == "0":
                    return

                choice = int(choice_str)
                if 1 <= choice <= max_choice:
                    selected_file = deleted_files[choice - 1]
                    self._handle_restore_deleted_file(selected_file)
                    return
                else:
                    self.console.print(
                        f"❌ [bold red]Please enter a number between 1 and {max_choice}.[/bold red]")

            except ValueError:
                self.console.print(
                    "❌ [bold red]Please enter a valid number.[/bold red]")
            except KeyboardInterrupt:
                return

    def _handle_restore_deleted_file(self, deleted_file: Dict) -> None:
        """Handle restoration of a specific deleted file."""
        backup_filename = deleted_file.get("backup_file")
        original_path = deleted_file.get("original_path")
        file_name = Path(original_path).name if original_path else "Unknown"

        confirm_text = Text()
        confirm_text.append(f"File: {file_name}\n", style="white")
        confirm_text.append(
            f"Original Path: {original_path}\n\n", style="cyan")

        try:
            backup_content = self.backup_manager.get_backup_content(
                original_path, 1)
            if backup_content and len(backup_content) < 1000:
                confirm_text.append("Preview:\n", style="bold white")
                lines = backup_content.split('\n')[:5]
                for line in lines:
                    if line.strip():
                        confirm_text.append(f"  {line}\n", style="dim white")
                if len(backup_content.split('\n')) > 5:
                    confirm_text.append(
                        "  ... (truncated)\n", style="dim white")
        except Exception:
            pass

        confirm_text.append(
            "\n[bold green]Ready to restore![/bold green]\n", style="")
        confirm_text.append(
            "[dim]Type 'yes' to restore this file, or anything else to cancel[/dim]", style="")

        self.console.print(Panel(
            confirm_text,
            title="🔄 RESTORE DELETED FILE",
            border_style="green",
            padding=(1, 2)
        ))

        try:
            prompt = Text("❯ ", style="bold cyan")
            confirmation = self.console.input(prompt).strip().lower()

            if confirmation == "yes":
                self.console.print(
                    "\n[bold blue]🔄 Restoring file...[/bold blue]")

                success = self.backup_manager.restore_deleted_file(
                    backup_filename)

                if success:
                    self.console.print(Panel(
                        f"✅ Successfully restored {file_name} to {original_path}",
                        title="🎉 RESTORATION COMPLETE",
                        border_style="green",
                        padding=(1, 2)
                    ))
                else:
                    self.console.print(Panel(
                        f"❌ Failed to restore {file_name}",
                        title="⚠️ RESTORATION FAILED",
                        border_style="red",
                        padding=(1, 2)
                    ))
            else:
                self.console.print(
                    "\n[yellow]❌ Restoration cancelled - file remains deleted[/yellow]")

        except KeyboardInterrupt:
            self.console.print(
                "\n[yellow]❌ Restoration cancelled - file remains deleted[/yellow]")

    def _handle_file_browser(self) -> None:
        """Handle file browser menu."""
        backed_files = self.backup_manager.get_all_backed_files()

        if not backed_files:
            self._show_no_backups_message()
            return

        table = Table(show_header=True, header_style="bold cyan",
                      border_style="blue")
        table.add_column("#", justify="right", style="white")
        table.add_column("File", style="white")
        table.add_column("Versions", justify="center", style="yellow")
        table.add_column("Last Backup", style="cyan")

        for i, file_path in enumerate(backed_files, 1):
            versions = self.backup_manager.get_file_versions(file_path)
            if versions:
                last_version = versions[-1]
                timestamp = datetime.fromisoformat(last_version["timestamp"])
                readable_time = timestamp.strftime("%Y-%m-%d %H:%M")
                file_name = Path(file_path).name
                table.add_row(str(i), file_name, str(
                    len(versions)), readable_time)

        self.console.print(Panel(
            table,
            title="📁 FILES WITH BACKUPS",
            border_style="green",
            padding=(1, 2)
        ))

        while True:
            try:
                max_choice = len(backed_files)
                choice_str = self.console.input(
                    f"\n👤 [bold cyan]Select file (1-{max_choice}) or 0 to cancel:[/bold cyan] ").strip()

                if choice_str == "0":
                    return

                choice = int(choice_str)
                if 1 <= choice <= max_choice:
                    selected_file = backed_files[choice - 1]
                    self._handle_file_versions(selected_file)
                    return
                else:
                    self.console.print(
                        f"❌ [bold red]Please enter a number between 1 and {max_choice}.[/bold red]")

            except ValueError:
                self.console.print(
                    "❌ [bold red]Please enter a valid number.[/bold red]")
            except KeyboardInterrupt:
                return

    def _handle_file_versions(self, file_path: str) -> None:
        """Handle version selection for a specific file."""
        versions = self.backup_manager.get_file_versions(file_path)

        if not versions:
            self.console.print(
                "❌ [bold red]No versions found for this file.[/bold red]")
            return

        table = Table(show_header=True, header_style="bold cyan",
                      border_style="blue")
        table.add_column("#", justify="right", style="white")
        table.add_column("Version", justify="center", style="yellow")
        table.add_column("Timestamp", style="cyan")
        table.add_column("Size", justify="right", style="white")

        for i, version in enumerate(reversed(versions), 1):
            timestamp = datetime.fromisoformat(version["timestamp"])
            readable_time = timestamp.strftime("%Y-%m-%d %H:%M")
            size_kb = f"{version['size'] // 1024}KB" if version['size'] >= 1024 else f"{version['size']}B"
            table.add_row(str(i), str(
                version["version"]), readable_time, size_kb)

        file_name = Path(file_path).name
        self.console.print(Panel(
            table,
            title=f"🔢 VERSIONS FOR {file_name.upper()}",
            border_style="blue",
            padding=(1, 2)
        ))

        while True:
            try:
                max_choice = len(versions)
                choice_str = self.console.input(
                    f"\n👤 [bold cyan]Select version (1-{max_choice}) or 0 to cancel:[/bold cyan] ").strip()

                if choice_str == "0":
                    return

                choice = int(choice_str)
                if 1 <= choice <= max_choice:

                    selected_version = versions[-choice]
                    self._handle_version_action(file_path, selected_version)
                    return
                else:
                    self.console.print(
                        f"❌ [bold red]Please enter a number between 1 and {max_choice}.[/bold red]")

            except ValueError:
                self.console.print(
                    "❌ [bold red]Please enter a valid number.[/bold red]")
            except KeyboardInterrupt:
                return

    def _handle_version_action(self, file_path: str, version_info: Dict) -> None:
        """Handle actions for a specific version."""
        file_name = Path(file_path).name
        version_num = version_info["version"]

        menu_text = Text()
        menu_text.append(f"File: {file_name}\n", style="bold white")
        menu_text.append(f"Version: {version_num}\n\n", style="cyan")

        menu_text.append("Choose an action:\n\n", style="bold cyan")
        menu_text.append("○ 1. 👀 Preview Changes\n", style="white")
        menu_text.append("○ 2. 🔄 Revert to This Version\n", style="green")
        menu_text.append("○ 3. 📄 View File Content\n", style="white")
        menu_text.append("○ 0. 🔙 Back to Versions\n", style="yellow")

        self.console.print(Panel(
            menu_text,
            title="⚡ VERSION ACTIONS",
            border_style="cyan",
            padding=(1, 2)
        ))

        while True:
            try:
                choice = self.console.input(
                    "\n👤 [bold cyan]Select action (0-3):[/bold cyan] ").strip()

                if choice == "0":
                    return

                elif choice == "1":
                    self._preview_changes(file_path, version_num)
                    continue

                elif choice == "2":
                    self._confirm_revert(file_path, version_num)
                    break

                elif choice == "3":
                    self._view_file_content(file_path, version_num)
                    continue

                else:
                    self.console.print(
                        "❌ [bold red]Please enter a number between 0 and 3.[/bold red]")

            except ValueError:
                self.console.print(
                    "❌ [bold red]Please enter a valid number.[/bold red]")
            except KeyboardInterrupt:
                return

    def _preview_changes(self, file_path: str, version_num: int) -> None:
        """Preview changes between current and backup version."""
        try:

            if Path(file_path).exists():
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    current_content = f.read()
            else:
                current_content = ""

            backup_content = self.backup_manager.get_backup_content(
                file_path, version_num)

            if backup_content is None:
                self.console.print(
                    "❌ [bold red]Could not load backup content.[/bold red]")
                return

            self.diff_viewer.show_diff(
                file_path, current_content, backup_content, version_num)

        except Exception as e:
            self.console.print(
                f"❌ [bold red]Error previewing changes: {str(e)}[/bold red]")

    def _confirm_revert(self, file_path: str, version_num: int) -> None:
        """Confirm and perform file revert."""
        file_name = Path(file_path).name

        confirm_text = Text()
        confirm_text.append(
            "⚠️  WARNING: This will overwrite the current file!\n\n", style="bold yellow")
        confirm_text.append(f"File: {file_name}\n", style="white")
        confirm_text.append(
            f"Revert to: Version {version_num}\n\n", style="cyan")
        confirm_text.append("This action cannot be undone.\n\n", style="red")
        confirm_text.append(
            "Type 'yes' to confirm, or anything else to cancel: ", style="bold white")

        self.console.print(Panel(
            confirm_text,
            title="🔄 CONFIRM REVERT",
            border_style="red",
            padding=(1, 2)
        ))

        try:
            prompt = Text("❯ ", style="bold cyan")
            confirmation = self.console.input(prompt).strip().lower()

            if confirmation == "yes":
                success = self.backup_manager.revert_file(
                    file_path, version_num)

                if success:
                    self.console.print(Panel(
                        f"✅ Successfully reverted {file_name} to version {version_num}",
                        title="🎉 REVERT COMPLETE",
                        border_style="green",
                        padding=(1, 2)
                    ))
                else:
                    self.console.print(Panel(
                        f"❌ Failed to revert {file_name}",
                        title="⚠️ REVERT FAILED",
                        border_style="red",
                        padding=(1, 2)
                    ))
            else:
                self.console.print("ℹ️ [yellow]Revert cancelled.[/yellow]")

        except KeyboardInterrupt:
            self.console.print("\nℹ️ [yellow]Revert cancelled.[/yellow]")

    def _view_file_content(self, file_path: str, version_num: int) -> None:
        """View content of a specific version."""
        content = self.backup_manager.get_backup_content(
            file_path, version_num)

        if content is None:
            self.console.print(
                "❌ [bold red]Could not load file content.[/bold red]")
            return

        self.diff_viewer.show_file_preview(file_path, content, version_num)

    def _handle_folder_browser(self) -> None:
        """Handle folder browser for batch operations."""
        self.console.print(Panel(
            "📂 Folder-level operations coming soon!\n\n"
            "For now, please use individual file operations.",
            title="🚧 FEATURE IN DEVELOPMENT",
            border_style="yellow",
            padding=(1, 2)
        ))

    def _handle_quick_revert(self) -> None:
        """Handle quick revert of last change."""
        backed_files = self.backup_manager.get_all_backed_files()

        if not backed_files:
            self._show_no_backups_message()
            return

        most_recent = None
        most_recent_time = None

        for file_path in backed_files:
            versions = self.backup_manager.get_file_versions(file_path)
            if versions:
                latest_version = versions[-1]
                version_time = datetime.fromisoformat(
                    latest_version["timestamp"])

                if most_recent_time is None or version_time > most_recent_time:
                    most_recent_time = version_time
                    most_recent = (file_path, latest_version)

        if most_recent:
            file_path, version_info = most_recent
            file_name = Path(file_path).name
            version_num = version_info["version"]

            confirm_text = Text()
            confirm_text.append(
                f"Last changed file: {file_name}\n", style="white")
            confirm_text.append(
                f"Revert to: Version {version_num}\n", style="cyan")
            confirm_text.append(
                f"Changed: {most_recent_time.strftime('%Y-%m-%d %H:%M')}\n\n", style="yellow")
            confirm_text.append(
                "Type 'yes' to revert, or 'no' to cancel: ", style="bold white")

            self.console.print(Panel(
                confirm_text,
                title="⚡ QUICK REVERT",
                border_style="cyan",
                padding=(1, 2)
            ))

            try:
                choice = self.console.input("").strip().lower()
                if choice == "yes":
                    success = self.backup_manager.revert_file(
                        file_path, version_num)
                    if success:
                        self.console.print(
                            "✅ [bold green]Quick revert completed![/bold green]")
                    else:
                        self.console.print(
                            "❌ [bold red]Quick revert failed![/bold red]")
                else:
                    self.console.print(
                        "ℹ️ [yellow]Quick revert cancelled.[/yellow]")
            except KeyboardInterrupt:
                self.console.print(
                    "\nℹ️ [yellow]Quick revert cancelled.[/yellow]")
        else:
            self.console.print(
                "❌ [bold red]No recent file versions found.[/bold red]")

    def _handle_cleanup(self) -> None:
        """Handle cleanup of old backups."""
        confirm_text = Text()
        confirm_text.append(
            "🧹 This will remove old file versions older than 30 days.\n\n", style="yellow")
        confirm_text.append(
            "Type 'yes' to proceed, or anything else to cancel: ", style="bold white")

        self.console.print(Panel(
            confirm_text,
            title="🧹 CLEAN UP VERSIONS",
            border_style="yellow",
            padding=(1, 2)
        ))

        try:
            choice = self.console.input("").strip().lower()
            if choice == "yes":
                self.backup_manager.cleanup_old_backups()
                self.console.print(
                    "✅ [bold green]Version cleanup completed![/bold green]")
            else:
                self.console.print("ℹ️ [yellow]Cleanup cancelled.[/yellow]")
        except KeyboardInterrupt:
            self.console.print("\nℹ️ [yellow]Cleanup cancelled.[/yellow]")

    def _handle_statistics(self) -> None:
        """Show backup statistics."""
        backed_files = self.backup_manager.get_all_backed_files()
        deleted_files = self.backup_manager.get_deleted_files()
        total_backups = 0
        total_size = 0

        for file_path in backed_files:
            versions = self.backup_manager.get_file_versions(file_path)
            total_backups += len(versions)
            for version in versions:
                total_size += version.get("size", 0)

        total_backups += len(deleted_files)
        for deleted_file in deleted_files:
            total_size += deleted_file.get("size", 0)

        total_files = len(backed_files) + len(deleted_files)

        stats_text = Text()
        stats_text.append(
            f"📁 Total files tracked: {total_files}\n", style="white")
        stats_text.append(f"🔢 Total backups: {total_backups}\n", style="cyan")
        stats_text.append(
            f"💾 Storage used: {total_size // 1024}KB\n", style="yellow")

        self.console.print(Panel(
            stats_text,
            title="📊 VERSION CONTROL INFO",
            border_style="blue",
            padding=(1, 2)
        ))

    def _show_no_backups_message(self) -> None:
        """Show message when no backups are available."""
        message = Text()
        message.append("📭 No backups found!\n\n", style="yellow")
        message.append(
            "Backups are created automatically when files are edited.\n", style="white")
        message.append(
            "Try editing some files first, then come back here.", style="dim white")

        self.console.print(Panel(
            message,
            title="📋 NO FILE VERSIONS",
            border_style="yellow",
            padding=(1, 2)
        ))
