#!/usr/bin/env python3
"""
Diff Viewer for Lyne VCS

Shows differences between file versions before reverting.
"""

import difflib
from pathlib import Path
from typing import List, Tuple, Optional, Dict
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.syntax import Syntax
from util.logging import get_logger

logger = get_logger("diff_viewer")


class DiffViewer:
    """Displays diffs between file versions."""

    def __init__(self):
        """Initialize diff viewer with rich console."""
        self.console = Console()

    def show_diff(self, file_path: str, current_content: str, backup_content: str,
                  version_num: int, max_lines: int = 50) -> None:
        """
        Show diff between current content and backup version.

        Args:
            file_path: Path to the file
            current_content: Current file content
            backup_content: Backup version content
            version_num: Version number being compared
            max_lines: Maximum lines to show in diff
        """
        try:
            file_path_obj = Path(file_path)
            filename = file_path_obj.name

            current_lines = current_content.splitlines(keepends=True)
            backup_lines = backup_content.splitlines(keepends=True)

            diff = list(difflib.unified_diff(
                backup_lines,
                current_lines,
                fromfile=f"a/{filename} (version {version_num})",
                tofile=f"b/{filename} (current)",
                lineterm='',
                n=3
            ))

            if not diff:
                self._show_no_changes_message(filename)
                return

            if len(diff) > max_lines:
                diff = diff[:max_lines]
                diff.append("... (truncated)")

            diff_text = self._format_diff(diff)

            changes = self._analyze_changes(diff)
            summary_text = self._create_summary(filename, version_num, changes)

            self.console.print(summary_text)
            self.console.print(diff_text)

        except Exception as e:
            self._show_error_message(str(e))

    def show_file_preview(self, file_path: str, content: str, version_num: int,
                          max_lines: int = 30) -> None:
        """
        Show preview of file content at a specific version.

        Args:
            file_path: Path to the file
            content: File content to preview
            version_num: Version number
            max_lines: Maximum lines to preview
        """
        try:
            file_path_obj = Path(file_path)
            filename = file_path_obj.name

            lines = content.splitlines()
            total_lines = len(lines)

            if total_lines > max_lines:
                preview_lines = lines[:max_lines]
                preview_content = '\n'.join(preview_lines)
                preview_content += f"\n\n... ({total_lines - max_lines} more lines)"
            else:
                preview_content = content

            syntax = Syntax(
                preview_content,
                self._get_language(filename),
                theme="monokai",
                line_numbers=True,
                word_wrap=True
            )

            panel = Panel(
                syntax,
                title=f"📄 {filename} - Version {version_num}",
                border_style="blue",
                padding=(1, 2)
            )

            self.console.print(panel)

        except Exception as e:
            self._show_error_message(str(e))

    def _format_diff(self, diff_lines: List[str]) -> Panel:
        """Format diff lines for rich display."""
        diff_text = Text()

        for line in diff_lines:
            if line.startswith('+++') or line.startswith('---') or line.startswith('@@'):
                diff_text.append(line + '\n', style="bold cyan")
            elif line.startswith('+'):
                diff_text.append(line + '\n', style="bold green")
            elif line.startswith('-'):
                diff_text.append(line + '\n', style="bold red")
            else:
                diff_text.append(line + '\n', style="white")

        return Panel(
            diff_text,
            title="🔍 CHANGES PREVIEW",
            border_style="yellow",
            padding=(1, 2)
        )

    def _analyze_changes(self, diff_lines: List[str]) -> Dict[str, int]:
        """Analyze the diff to count additions, deletions, and context lines."""
        additions = 0
        deletions = 0
        context = 0

        for line in diff_lines:
            if line.startswith('+') and not line.startswith('+++'):
                additions += 1
            elif line.startswith('-') and not line.startswith('---'):
                deletions += 1
            elif not line.startswith('@@'):
                context += 1

        return {
            'additions': additions,
            'deletions': deletions,
            'context': context
        }

    def _create_summary(self, filename: str, version_num: int, changes: Dict[str, int]) -> Panel:
        """Create a summary panel for the diff."""
        summary_text = Text()
        summary_text.append(f"📝 File: {filename}\n", style="bold white")
        summary_text.append(
            f"🔢 Comparing: Version {version_num} → Current\n\n", style="cyan")

        summary_text.append("📊 Changes:\n", style="bold yellow")
        summary_text.append(
            f"  ➕ Added: {changes['additions']} lines\n", style="green")
        summary_text.append(
            f"  ➖ Removed: {changes['deletions']} lines\n", style="red")
        summary_text.append(
            f"  📄 Context: {changes['context']} lines\n", style="white")

        if changes['additions'] > 0 or changes['deletions'] > 0:
            summary_text.append(
                "\n⚠️  This revert will modify the file!\n", style="bold yellow")
        else:
            summary_text.append("\n✅ No changes detected\n", style="green")

        return Panel(
            summary_text,
            title="📋 DIFF SUMMARY",
            border_style="cyan",
            padding=(1, 2)
        )

    def _show_no_changes_message(self, filename: str) -> None:
        """Show message when no changes are detected."""
        message = Text()
        message.append("✅ No changes detected!\n\n", style="bold green")
        message.append(
            f"The file '{filename}' is identical to the backup version.\n", style="white")
        message.append("No revert needed.", style="dim white")

        self.console.print(Panel(
            message,
            title="📋 COMPARISON RESULT",
            border_style="green",
            padding=(1, 2)
        ))

    def _show_error_message(self, error: str) -> None:
        """Show error message."""
        message = Text()
        message.append("❌ Error displaying diff:\n\n", style="bold red")
        message.append(str(error), style="white")

        self.console.print(Panel(
            message,
            title="⚠️ DIFF ERROR",
            border_style="red",
            padding=(1, 2)
        ))

    def _get_language(self, filename: str) -> str:
        """Determine syntax highlighting language from filename."""
        ext = Path(filename).suffix.lower()

        language_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.html': 'html',
            '.css': 'css',
            '.json': 'json',
            '.xml': 'xml',
            '.md': 'markdown',
            '.txt': 'text',
            '.sql': 'sql',
            '.sh': 'bash',
            '.yml': '.yaml',
            '.yaml': 'yaml'
        }

        return language_map.get(ext, 'text')
