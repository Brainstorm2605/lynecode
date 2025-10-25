"""
This is the main entry point for the Lyne tool, providing a terminal interface
for users to interact with the agent system.
"""

import os
import sys
import time
import argparse
import json
import re
import shutil
import select
from pathlib import Path
from typing import Dict, Any, List, Optional
from agent.agent import Agent
from prompt_manager import PromptManager
from model_manager.model_manager import ModelManager
from tool_spec.lyne_tool_spec import LYNE_TOOL_SPEC
from chat_menu import ChatMenu

from tool import (
    create_file, create_folder,
    delete_file, delete_folder,
    write_lines, replace_lines, delete_lines,
    block_edit_file,
    fetch_content, read_many_files,
    grep_search, search_and_read,
    ast_grep_search,
    search_index,
    web_search, read_web_page,
    file_exists, folder_exists, get_folder_structure, get_file_info,
    find_files_by_pattern, get_path_type, get_common_paths,
    get_git_changes,
    linting_checker,
    run_terminal_command,
    semgrep_scan
)


from util.logging import get_logger, setup_logging
from util.filesystem_indexer import FileSystemIndexer

try:
    from rich.console import Console, Group
    from rich.panel import Panel
    from rich.text import Text
    from rich.table import Table
    from rich.syntax import Syntax
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


class NavigationContext:
    """Handles navigation context preservation during menu transitions."""

    def __init__(self):
        self.context_stack = []

    def save_conversation_context(self, agent, conversation_id, current_path):
        """Save current conversation context for later restoration."""
        context = {
            'conversation_id': conversation_id,
            'current_path': current_path,
            'agent_model': getattr(agent, 'current_model', None),
            'agent_state': agent.get_session_summary() if hasattr(agent, 'get_session_summary') else None,
            'timestamp': str(Path.cwd())
        }
        self.context_stack.append(context)
        return context

    def get_current_context(self):
        """Get the most recent navigation context."""
        return self.context_stack[-1] if self.context_stack else None

    def clear_context(self):
        """Clear the navigation context stack."""
        self.context_stack.clear()

    def has_context(self):
        """Check if there's a saved navigation context."""
        return len(self.context_stack) > 0


try:
    from colorama import init, Fore, Style
    init(autoreset=True)
    COLORAMA_AVAILABLE = True
except ImportError:
    COLORAMA_AVAILABLE = False


def display_navigation_menu() -> None:
    """Display the main navigation menu during conversation."""
    menu_text = Text()
    menu_text.append("Choose a navigation option:\n\n", style="bold cyan")

    menu_text.append("○ 1. 🏠 Back to Main Menu\n", style="white")
    menu_text.append("○ 2. 💬 Switch Conversations\n", style="white")
    menu_text.append("○ 3. ⚙️ Model Settings\n", style="white")
    menu_text.append("○ 4. ❓ Show All Commands\n", style="white")
    menu_text.append("○ 5. 🔄 Version Control\n", style="green")
    menu_text.append("○ 6. 🔑 API Configuration\n", style="bold yellow")
    menu_text.append(
        "○ 7. ❌ Cancel (Return to Conversation)\n", style="red")

    console.print(Panel(
        menu_text,
        title="🔄 NAVIGATION MENU",
        border_style="blue",
        title_align="center",
        padding=(1, 2)
    ))


def display_help_menu() -> None:
    """Display comprehensive help with all available commands."""
    from rich.text import Text

    help_text = Text()

    help_text.append("💬 Conversation Commands:\n", style="bold cyan")
    help_text.append("  /menu     - Show navigation menu\n", style="white")
    help_text.append("  /back     - Go to main menu\n", style="white")
    help_text.append("  /chats    - Switch conversations\n", style="white")
    help_text.append("  /help     - Show this help menu\n\n", style="white")

    help_text.append("🤖 Model Commands:\n", style="bold cyan")
    help_text.append(
        "  /switch <model>  - Switch to specific model\n", style="white")
    help_text.append(
        "  /model           - Go to model settings (may lose context)\n\n", style="white")

    help_text.append("📎 Attachment Commands:\n", style="bold cyan")
    help_text.append(
        "  /attachments         - List current attachments\n", style="white")
    help_text.append(
        "  /detach <term|all>   - Detach matching attachment or clear all\n", style="white")
    help_text.append(
        "  Inline attach        - Use /file:<name> or /folder:<name> inside your query (one per query)\n\n", style="white")

    help_text.append("🚪 System Commands:\n", style="bold cyan")
    help_text.append("  quit      - Exit application\n", style="white")
    help_text.append("  Ctrl+C    - Interrupt and exit\n\n", style="white")

    help_text.append(
        "💡 Tip: Use /menu for the most comprehensive navigation experience!", style="dim italic")

    console.print(Panel(
        help_text,
        title="📋 AVAILABLE COMMANDS",
        border_style="green",
        title_align="center",
        padding=(1, 2)
    ))


def get_navigation_choice() -> int:
    """Get user choice from navigation menu."""
    while True:
        if RICH_AVAILABLE:
            prompt = Text("Select option (1-7): ", style="bold cyan")
            choice_str = console.input(prompt).strip()
        else:
            choice_str = input("Select option (1-7): ").strip()

        if not choice_str:
            continue

        try:
            choice_num = int(choice_str)
            if 1 <= choice_num <= 7:
                return choice_num
            else:
                if RICH_AVAILABLE:
                    console.print(
                        f"❌ [bold red]Please enter a number between 1 and 7.[/bold red]")
                else:
                    print("Please enter a number between 1 and 7.")
        except ValueError:
            if RICH_AVAILABLE:
                console.print(
                    "❌ [bold red]Please enter a valid number.[/bold red]")
            else:
                print("Please enter a valid number.")


setup_logging()
logger = get_logger("main")
console = Console() if RICH_AVAILABLE else None


def get_colored_text(text: str, color=None, bright=False) -> str:
    """Return colored text using rich or colorama."""
    if RICH_AVAILABLE:
        style = "bold " if bright else ""
        style += color if color else ""
        return f"[{style}]{text}[/{style}]"

    if not COLORAMA_AVAILABLE:
        return text

    color_code = getattr(Fore, color.upper()) if color else ""
    style_code = Style.BRIGHT if bright else ""
    return f"{style_code}{color_code}{text}{Style.RESET_ALL}"


def print_banner():
    """Display the welcome banner."""
    banner = r"""    ██╗  ██╗   ██╗███╗   ██╗███████╗     ██████╗ ██████╗ ██████╗ ███████╗
    ██║  ╚██╗ ██╔╝████╗  ██║██╔════╝    ██╔════╝██╔═══██╗██╔══██╗██╔════╝
    ██║   ╚████╔╝ ██╔██╗ ██║█████╗      ██║     ██║   ██║██║  ██║█████╗  
    ██║    ╚██╔╝  ██║╚██╗██║██╔══╝      ██║     ██║   ██║██║  ██║██╔══╝  
    ███████╗██║   ██║ ╚████║███████╗    ╚██████╗╚██████╔╝██████╔╝███████╗
    ╚══════╝╚═╝   ╚═╝  ╚═══╝╚══════╝     ╚═════╝ ╚═════╝ ╚═════╝ ╚══════╝"""

    terminal_width = shutil.get_terminal_size().columns

    print("\n")
    for line in banner.split('\n'):
        print(line.center(terminal_width))

    prompt_message = "Type your query or use /menu for navigation, /help for commands"
    print(prompt_message.center(terminal_width))


def setup_agent(current_path: str, model_manager: ModelManager, selected_model: Optional[str] = None, conversation_id: Optional[str] = None) -> Agent:
    """Set up and configure the agent with all necessary components silently."""
    try:
        agent = Agent("", current_path, max_iterations=25,
                      conversation_id=conversation_id)
        prompt_manager = PromptManager()
        agent.set_prompt_manager(prompt_manager)

        if selected_model:
            try:
                llm_adapter = model_manager.create_adapter_for_model(
                    selected_model)
                if not llm_adapter:

                    validation = model_manager.validate_model_availability(
                        selected_model)
                    error_msg = validation.get(
                        "error", f"Failed to create adapter for model: {selected_model}")

                    if RICH_AVAILABLE:
                        console.print(Panel(
                            f"[bold red]Unable to use model: {selected_model}[/bold red]\n\n"
                            f"[yellow]{error_msg}[/yellow]\n\n"
                            "Please use the API Configuration menu to set up your keys.",
                            title="[bold red]Model Configuration Issue[/bold red]",
                            border_style="red",
                            padding=(1, 2)
                        ))
                    else:
                        print(get_colored_text(
                            f"Unable to use model: {selected_model}", "red"))
                        print(get_colored_text(error_msg, "yellow"))
                        print(get_colored_text(
                            "Please use the API Configuration menu to set up your keys.", "yellow"))
                    sys.exit(1)
            except Exception as e:
                if RICH_AVAILABLE:
                    console.print(Panel(
                        f"[bold red]Error initializing model: {selected_model}[/bold red]\n\n"
                        f"[yellow]{str(e)}[/yellow]\n\n"
                        "Please use the API Configuration menu to set up your keys.",
                        title="[bold red]Model Error[/bold red]",
                        border_style="red",
                        padding=(1, 2)
                    ))
                else:
                    print(get_colored_text(
                        f"Error initializing model: {selected_model}", "red"))
                    print(get_colored_text(str(e), "yellow"))
                    print(get_colored_text(
                        "Please use the API Configuration menu to set up your keys.", "yellow"))
                sys.exit(1)
        else:

            default_model = model_manager.get_default_model()
            if default_model:
                try:
                    llm_adapter = model_manager.create_adapter_for_model(
                        default_model)
                    if not llm_adapter:

                        validation = model_manager.validate_model_availability(
                            default_model)
                        error_msg = validation.get(
                            "error", f"Failed to create adapter for default model: {default_model}")

                        if RICH_AVAILABLE:
                            console.print(Panel(
                                f"[bold red]Unable to use default model: {default_model}[/bold red]\n\n"
                                f"[yellow]{error_msg}[/yellow]\n\n"
                                "Please use the API Configuration menu to set up your keys.",
                                title="[bold red]Default Model Issue[/bold red]",
                                border_style="red",
                                padding=(1, 2)
                            ))
                        else:
                            print(get_colored_text(
                                f"Unable to use default model: {default_model}", "red"))
                            print(get_colored_text(error_msg, "yellow"))
                            print(get_colored_text(
                                "Please use the API Configuration menu to set up your keys.", "yellow"))
                        sys.exit(1)
                except Exception as e:
                    if RICH_AVAILABLE:
                        console.print(Panel(
                            f"[bold red]Error initializing default model: {default_model}[/bold red]\n\n"
                            f"[yellow]{str(e)}[/yellow]\n\n"
                            "Please use the API Configuration menu to set up your keys.",
                            title="[bold red]Default Model Error[/bold red]",
                            border_style="red",
                            padding=(1, 2)
                        ))
                    else:
                        print(get_colored_text(
                            f"Error initializing default model: {default_model}", "red"))
                        print(get_colored_text(str(e), "yellow"))
                        print(get_colored_text(
                            "Please use the API Configuration menu to set up your keys.", "yellow"))
                    sys.exit(1)
            else:

                if RICH_AVAILABLE:
                    console.print(Panel(
                        "🌟 [bold cyan]Welcome to Lyne![/bold cyan]\n\n"
                        "🤖 [yellow]No AI models are currently configured.[/yellow]\n\n"
                        "To start chatting with AI, you'll need to configure API keys using the API Configuration menu:\n\n"
                        "• [green]Use the API Configuration menu (option 3) to securely set up your keys\n\n"
                        "[dim]Configure your API keys through the menu to start chatting![/dim]",
                        title="[bold blue]🚀 Getting Started[/bold blue]",
                        border_style="blue",
                        padding=(1, 2)
                    ))
                else:
                    print(get_colored_text("Welcome to Lyne!", "cyan", True))
                    print(get_colored_text(
                        "No AI models are currently configured.", "yellow"))
                    print()
                    print(get_colored_text(
                        "To start chatting with AI, you'll need to configure API keys:", "white"))
                    print(get_colored_text(
                        "• Use the API Configuration menu (option 3) to securely set up your keys", "green"))
                    print()
                    print(get_colored_text(
                        "Configure your API keys through the menu to start chatting!", "white"))
                sys.exit(0)

        actual_model = selected_model
        if not selected_model:
            actual_model = model_manager.get_default_model()
        agent.set_llm_adapter(llm_adapter, actual_model)
        agent.set_model_manager(model_manager)
        agent.set_tool_spec_sheet(LYNE_TOOL_SPEC)
        register_tools(agent)
        return agent
    except Exception as e:
        if RICH_AVAILABLE:
            console.print(Panel(
                f"[bold red]Error[/bold red]: Failed to set up agent: {e}", border_style="red"))
        else:
            print(get_colored_text(
                f"[Error] Failed to set up agent: {str(e)}", "red"))
        sys.exit(1)


def register_tools(agent: Agent):
    """Register all available tools with the agent."""
    tools = {
        "create_file": (create_file, "Create a new file with optional content"),
        "create_folder": (create_folder, "Create a new directory structure"),
        "delete_file": (delete_file, "Delete a single file"),
        "delete_folder": (delete_folder, "Delete a directory with optional recursive deletion"),
        "write_lines": (write_lines, "Insert new content at a specific line in a file"),
        "replace_lines": (replace_lines, "Replace a range of lines with new content"),
        "delete_lines": (delete_lines, "Delete a range of lines from a file"),
        "block_edit_file": (block_edit_file, "Perform context aware block editing of a file"),
        "fetch_content": (fetch_content, "Read file content with line range support"),
        "read_many_files": (read_many_files, "Read multiple files using glob patterns"),
        "grep_search": (grep_search, "Search for patterns in files"),
        "search_and_read": (search_and_read, "Search and read context in one operation"),
        "ast_grep_search": (ast_grep_search, "Search for structural patterns using AST"),
        "search_index": (search_index, "Fuzzy NAME search over files and folders using Lyne's local index"),
        "web_search": (web_search, "Search the web (no paid APIs) and return formatted results"),
        "read_web_page": (read_web_page, "Fetch and extract readable text from a web page with guardrails"),
        "file_exists": (file_exists, "Check if a file exists"),
        "folder_exists": (folder_exists, "Check if a folder exists"),
        "get_folder_structure": (get_folder_structure, "Get the structure of a folder"),
        "get_file_info": (get_file_info, "Get information about a file"),
        "find_files_by_pattern": (find_files_by_pattern, "Find files matching a pattern"),
        "get_path_type": (get_path_type, "Determine if a path is a file or folder"),
        "get_common_paths": (get_common_paths, "Get common paths in a directory"),
        "get_git_changes": (get_git_changes, "Read git changes including status, diff, and commit history"),
        "linting_checker": (linting_checker, "Check code quality issues in multiple files using appropriate linters for each language"),
        "run_terminal_command": (run_terminal_command, "Run a terminal command within the project path with guardrails and confirmation"),
        "semgrep_scan": (semgrep_scan, "Run Semgrep on a path with optional config and return findings")
    }
    for name, (func, desc) in tools.items():
        agent.register_tool(name, func, desc)


class ResponseFormatter:
    """ Response formatter that handles all markdown elements reliably."""

    def __init__(self):
        self.rich_available = RICH_AVAILABLE
        self.colorama_available = COLORAMA_AVAILABLE

    def format_headers(self, content: str) -> str:
        """Format markdown headers with proper styling."""
        if not self.rich_available:
            return content

        patterns = [
            (r'^####\s+(.+)$', r'[bold blue]\1[/bold blue]'),
            (r'^###\s+(.+)$',
             r'[bold cyan underline]\1[/bold cyan underline]'),
            (r'^##\s+(.+)$', r'[bold magenta]\1[/bold magenta]'),
            (r'^#\s+(.+)$', r'[bold yellow]\1[/bold yellow]'),
        ]

        for pattern, replacement in patterns:
            content = re.sub(pattern, replacement, content, flags=re.MULTILINE)

        return content

    def format_text_styles(self, content: str) -> str:
        """Format bold, italic, and other text styles."""
        if not self.rich_available:
            return content

        content = re.sub(r'\*\*(.*?)\*\*', r'[bold]\1[/bold]', content)
        content = re.sub(r'`([^`]+)`', r'[cyan]\1[/cyan]', content)

        def replace_italic(match):
            text = match.group(1)
            if text and not text.isspace():
                return f'[italic]{text}[/italic]'
            return match.group(0)

        content = re.sub(
            r'(?<!\*)\*([^*\n]+?)\*(?!\*)', replace_italic, content)

        return content

    def extract_and_format_tables(self, content: str):
        """Extract markdown tables and convert them to Rich Table objects."""
        tables = []

        if not self.rich_available:
            return content, tables

        def process_table(match):
            table_content = match.group(0)
            lines = [line.strip()
                     for line in table_content.strip().split('\n') if line.strip()]

            if len(lines) < 3:
                return table_content

            try:
                header_line = lines[0]
                if not (header_line.startswith('|') and header_line.endswith('|')):
                    return table_content

                headers = [h.strip() for h in header_line.strip(
                    '|').split('|') if h.strip()]

                data_rows = []
                for line in lines[2:]:
                    if line.startswith('|') and line.endswith('|'):
                        row_data = [cell.strip()
                                    for cell in line.strip('|').split('|')]
                        if len(row_data) >= len(headers):
                            data_rows.append(row_data[:len(headers)])

                if not data_rows:
                    return table_content

                table = Table(
                    show_header=True,
                    header_style="bold cyan",
                    border_style="blue",
                    show_lines=True,
                    expand=True
                )

                for header in headers:
                    table.add_column(header, style="white", justify="left")

                for row_data in data_rows:
                    table.add_row(*row_data)

                tables.append(table)
                return f"__TABLE_{len(tables)-1}__"

            except Exception:
                return table_content

        table_pattern = r'^\|.*\|.*\n\|[-:\s|]+\|\n(?:\|.*\|.*\n)*'
        content = re.sub(table_pattern, process_table,
                         content, flags=re.MULTILINE)

        return content, tables

    def extract_and_format_code_blocks(self, content: str):
        """Extract and format code blocks."""
        code_blocks = []

        if not self.rich_available:
            def replace_code_plain(match):
                code_content = match.group(1).strip()
                return f"\n--- Code Block ---\n{code_content}\n--- End Code ---\n"
            return re.sub(r'<codepart>(.*?)</codepart>', replace_code_plain, content, flags=re.DOTALL), code_blocks

        def process_code_block(match):
            code_content = match.group(1).strip()

            language = "text"
            if any(keyword in code_content for keyword in ["def ", "import ", "class ", "if __name__"]):
                language = "python"
            elif any(keyword in code_content for keyword in ["function", "const ", "let ", "var "]):
                language = "javascript"
            elif any(keyword in code_content for keyword in ["public class", "private ", "public static"]):
                language = "java"
            elif any(keyword in code_content for keyword in ["#include", "int main", "std::"]):
                language = "cpp"
            elif "<" in code_content and ">" in code_content and any(tag in code_content for tag in ["<div", "<html", "<body"]):
                language = "html"

            syntax_obj = Syntax(
                code_content,
                language,
                theme="monokai",
                line_numbers=True,
                word_wrap=True
            )

            code_blocks.append(syntax_obj)
            return f"__CODE_BLOCK_{len(code_blocks)-1}__"

        content = re.sub(r'<codepart>(.*?)</codepart>',
                         process_code_block, content, flags=re.DOTALL)

        def process_markdown_code(match):
            language = match.group(1) or "text"
            code_content = match.group(2).strip()

            syntax_obj = Syntax(
                code_content,
                language,
                theme="monokai",
                line_numbers=True,
                word_wrap=True
            )

            code_blocks.append(syntax_obj)
            return f"__CODE_BLOCK_{len(code_blocks)-1}__"

        content = re.sub(r'```(\w*)\n(.*?)\n```',
                         process_markdown_code, content, flags=re.DOTALL)

        return content, code_blocks

    def format_tree_diagrams(self, content: str) -> str:
        """Format tree diagrams with proper styling."""
        if not self.rich_available:
            return content

        def process_tree(match):
            tree_content = match.group(1).strip()
            return f"[green]{tree_content}[/green]"

        pattern = r'<\s*(?:treediagram|tre-diagram|trediagram)\s*>([\s\S]*?)<\s*/\s*(?:treediagram|tre-diagram|trediagram)\s*>'
        return re.sub(pattern, process_tree, content, flags=re.IGNORECASE)

    def format_lists(self, content: str) -> str:
        """Format bullet points and numbered lists."""
        if not self.rich_available:
            return content

        content = re.sub(r'^[-*+]\s+(.+)$', r'• \1',
                         content, flags=re.MULTILINE)
        content = re.sub(r'^\d+\.\s+(.+)$',
                         r'[cyan]\g<0>[/cyan]', content, flags=re.MULTILINE)

        return content

    def create_fallback_formatting(self, content: str) -> str:
        """Create fallback formatting for non-Rich environments."""
        if self.rich_available:
            return content

        content = re.sub(r'^####\s+(.+)$', r'    \1',
                         content, flags=re.MULTILINE)
        content = re.sub(r'^###\s+(.+)$', r'  \1', content, flags=re.MULTILINE)
        content = re.sub(r'^##\s+(.+)$', r' \1', content, flags=re.MULTILINE)
        content = re.sub(r'^#\s+(.+)$', r'\1', content, flags=re.MULTILINE)
        content = re.sub(r'\*\*(.*?)\*\*', r'\1', content)
        content = re.sub(r'\*(.*?)\*', r'\1', content)

        return content

    def format_agent_response(self, response: str) -> None:
        """Main method to format and display agent responses with robust error handling."""
        if not response or not response.strip():
            if self.rich_available:
                console.print(
                    Panel("[bold red]No response from agent.[/bold red]", border_style="red"))
            else:
                print("[No response from agent]")
            return

        try:
            content, tables = self.extract_and_format_tables(response)
            content, code_blocks = self.extract_and_format_code_blocks(content)
            content = self.format_tree_diagrams(content)
            content = self.format_headers(content)
            content = self.format_text_styles(content)
            content = self.format_lists(content)

            if self.rich_available:
                self._display_rich_content(content, tables, code_blocks)
            else:
                self._display_plain_content(content)

        except Exception as e:
            error_msg = f"Formatting error: {str(e)}"

            if self.rich_available:
                console.print(Panel(
                    f"[yellow]{error_msg}[/yellow]\n\n{response}",
                    title="[yellow]Formatting Warning[/yellow]",
                    border_style="yellow",
                    padding=(1, 2)
                ))
            else:
                print(f"\n[Warning] {error_msg}\n")
                print("="*80)
                print(response)
                print("="*80)

    def _display_rich_content(self, content: str, tables, code_blocks) -> None:
        """Display content using Rich formatting."""
        from rich.markup import render
        from rich.console import Group

        display_elements = []
        parts = content.split('\n')
        current_text_lines = []

        for part in parts:

            table_match = re.search(r'__TABLE_(\d+)__', part)
            if table_match:

                if current_text_lines:
                    text_content = '\n'.join(current_text_lines)
                    if text_content.strip():

                        rendered_text = console.render_str(text_content)
                        display_elements.append(Text.from_markup(text_content))
                    current_text_lines = []

                table_index = int(table_match.group(1))
                if table_index < len(tables):
                    display_elements.append(tables[table_index])
                continue

            code_match = re.search(r'__CODE_BLOCK_(\d+)__', part)
            if code_match:

                if current_text_lines:
                    text_content = '\n'.join(current_text_lines)
                    if text_content.strip():
                        display_elements.append(Text.from_markup(text_content))
                    current_text_lines = []

                code_index = int(code_match.group(1))
                if code_index < len(code_blocks):
                    display_elements.append(code_blocks[code_index])
                continue

            current_text_lines.append(part)

        if current_text_lines:
            text_content = '\n'.join(current_text_lines)
            if text_content.strip():
                display_elements.append(Text.from_markup(text_content))

        if display_elements:
            if len(display_elements) == 1:
                display_content = display_elements[0]
            else:
                display_content = Group(*display_elements)

            console.print(Panel(
                display_content,
                title="[bold green]Agent Response[/bold green]",
                border_style="green",
                padding=(1, 2)
            ))
        else:

            console.print(Panel(
                Text.from_markup(content) if content.strip(
                ) else "No content to display",
                title="[bold green]Agent Response[/bold green]",
                border_style="green",
                padding=(1, 2)
            ))

    def _display_plain_content(self, content: str) -> None:
        """Display content in plain text format."""
        content = self.create_fallback_formatting(content)
        terminal_width = min(80, shutil.get_terminal_size().columns)
        border = "="*terminal_width

        print(f"\n{border}")
        print("AGENT RESPONSE")
        print(f"{border}")
        print(content)
        print(f"{border}")


_formatter = ResponseFormatter()


def format_agent_response(response: str) -> None:
    """Format and display agent responses with robust error handling."""
    display_text = response

    try:
        parsed = json.loads(response)
    except (TypeError, json.JSONDecodeError):
        parsed = None

    if isinstance(parsed, dict):
        action = str(parsed.get("action", "")).strip().lower()
        if action == "summaries":
            sections = []

            summary_text = parsed.get("summary")
            if isinstance(summary_text, str) and summary_text.strip():
                sections.append(summary_text.strip())

            milestones = parsed.get("achieved_milestone") or parsed.get(
                "achieved_milestones")
            if isinstance(milestones, str):
                milestones = [milestones]
            if isinstance(milestones, list):
                milestone_lines = [item for item in milestones if isinstance(
                    item, str) and item.strip()]
                if milestone_lines:
                    sections.append("\nAchieved milestones:")
                    sections.extend(
                        [f"- {line.strip()}" for line in milestone_lines])

            if sections:
                display_text = "\n".join(sections)

    _formatter.format_agent_response(display_text)


def handle_model_selection(model_manager: ModelManager, chat_menu: ChatMenu) -> Optional[str]:
    """Handle model selection during chat session."""
    try:
        result = chat_menu._run_model_menu(model_manager)
        return result
    except Exception as e:
        if RICH_AVAILABLE:
            console.print(Panel(
                f"[bold red]Error selecting model: {str(e)}[/bold red]",
                title="[bold red]Model Selection Error[/bold red]",
                border_style="red",
                padding=(1, 2)
            ))
        else:
            print(get_colored_text(
                f"[Error] Error selecting model: {str(e)}", "red"))
        return None


def run_query(agent: Agent, query: str) -> str:
    """Run a query through the agent and return the result."""
    try:
        agent.query = query
        agent.reset_session()
        current_path = agent.current_path
        if not Path(current_path).exists():
            error_response = f"[Error] Cannot process query: The path '{current_path}' does not exist."
            agent.save_to_conversation_history(error_response)
            return error_response

        result = agent.run()

        agent.save_to_conversation_history(result)
        return result
    except Exception as e:
        error_response = f"[Error] Failed to process query: {str(e)}"
        agent.save_to_conversation_history(error_response)
        return error_response


def get_multiline_input(prompt_text: str = "\n> ") -> str:
    """
    Get user input handling multiline paste properly.
    Reads all available input including pasted multi-line text.
    """
    lines = []

    if os.name == 'nt':
        import msvcrt
        if RICH_AVAILABLE:
            console.print(Text(prompt_text, style="bold cyan"), end="")
        else:
            print(get_colored_text(prompt_text, "cyan", True), end="", flush=True)

        first_line = sys.stdin.readline().rstrip('\r\n')
        lines.append(first_line)

        while msvcrt.kbhit():
            extra_line = sys.stdin.readline().rstrip('\r\n')
            if extra_line or lines:
                lines.append(extra_line)
            else:
                break
    else:
        if RICH_AVAILABLE:
            console.print(Text(prompt_text, style="bold cyan"), end="")
        else:
            print(get_colored_text(prompt_text, "cyan", True), end="", flush=True)

        first_line = sys.stdin.readline().rstrip('\n')
        lines.append(first_line)

        try:
            while select.select([sys.stdin], [], [], 0.0)[0]:
                extra_line = sys.stdin.readline().rstrip('\n')
                if extra_line or lines:
                    lines.append(extra_line)
                else:
                    break
        except:
            pass

    result = '\n'.join(lines)
    return result.strip()


def main():
    """Main entry point for the application."""
    parser = argparse.ArgumentParser(
        description="Lyne: Intelligent File & Text Manipulation System")
    parser.add_argument("path", nargs="?", default=os.getcwd(
    ), help="Path to operate on (defaults to current directory)")
    args, _ = parser.parse_known_args()

    try:
        current_path = str(Path(args.path).resolve())

        os.environ['LYNE_OPERATING_PATH'] = current_path
        time_machine_dir = Path(current_path) / "time_machine"
        try:
            time_machine_dir.mkdir(parents=True, exist_ok=True)
            if os.name == 'nt':
                import ctypes
                ctypes.windll.kernel32.SetFileAttributesW(
                    str(time_machine_dir), 0x02 | 0x04)
        except Exception:
            pass

    except Exception as e:
        if RICH_AVAILABLE:
            console.print(Panel(
                f"[bold red]Invalid path: {e}. Falling back to current directory.[/bold red]",
                title="[bold red]Path Error[/bold red]",
                border_style="red",
                padding=(1, 2)
            ))
        else:
            print(get_colored_text(
                f"[Error] Invalid path: {str(e)}. Falling back to current directory.", "red"))
        current_path = str(Path(os.getcwd()).resolve())

    print_banner()

    if RICH_AVAILABLE:
        with console.status("[bold green]Building project index...[/bold green]"):
            indexer = FileSystemIndexer(current_path)
            indexer.build_index()
    else:
        indexer = FileSystemIndexer(current_path)
        indexer.build_index()

    try:
        if RICH_AVAILABLE:
            with console.status("[bold green]Cleaning up old VCS backups...[/bold green]"):
                from vcs.backup_manager import BackupManager
                backup_mgr = BackupManager(current_path)
        else:
            from vcs.backup_manager import BackupManager
            backup_mgr = BackupManager(current_path)
    except Exception:
        pass

    try:
        model_manager = ModelManager()
    except Exception as e:

        try:
            model_manager = ModelManager()
        except Exception:

            model_manager = ModelManager.__new__(ModelManager)
            model_manager.providers = {
                "openai": None, "gemini": None, "azure": None}

    chat_menu = ChatMenu(project_path=current_path)
    conversation_id, selected_model = chat_menu.run_menu(model_manager)

    if conversation_id == "":
        if RICH_AVAILABLE:
            console.print(
                "\n[bold yellow]Thank you for using Lyne. Goodbye![/bold yellow]")
        else:
            print(get_colored_text("\nThank you for using Lyne. Goodbye!", "yellow"))
        return

    agent = setup_agent(current_path, model_manager,
                        selected_model, conversation_id)

    def format_model_name(model):
        if "-thinking" in model:
            return model.replace("-thinking", " 🧠")
        return model

    if selected_model:
        display_name = format_model_name(selected_model)
        if RICH_AVAILABLE:
            console.print(
                f"🤖 [bold cyan]Using model: {display_name}[/bold cyan]")
        else:
            print(get_colored_text(f"🤖 Using model: {display_name}", "cyan"))
    else:
        default_model = model_manager.get_default_model()
        if default_model:
            display_name = format_model_name(default_model)
            if RICH_AVAILABLE:
                console.print(
                    f"🤖 [bold cyan]Using default model: {display_name}[/bold cyan]")
            else:
                print(get_colored_text(
                    f"🤖 Using default model: {display_name}", "cyan"))

    if not Path(current_path).exists():
        if RICH_AVAILABLE:
            console.print(Panel(
                f"[bold yellow]Working with non-existent path: {current_path}[/bold yellow]",
                title="[bold yellow]Path Warning[/bold yellow]",
                border_style="yellow",
                padding=(1, 2)
            ))
        else:
            print(get_colored_text(
                f"[Warning] Working with non-existent path: {current_path}", "yellow"))

    if RICH_AVAILABLE:
        console.print("💬 [bold cyan]Enter your query below:[/bold cyan]")
        console.print(
            "\n💡 [dim]Navigation: /menu • /back • /chats • Help: /help • Models: /model • /switch <model> • Attach: inline /file:<name> or /folder:<name> • /attachments • /detach <term> • Quit: quit[/dim]")
    else:
        print(get_colored_text("💬 Enter your query below:", "cyan"))
        print(get_colored_text(
            "💡 Navigation: /menu • /back • /chats • Help: /help • Models: /model • /switch <model> • Attach: inline /file:<name> or /folder:<name> • /attachments • /detach <term> • Quit: quit", "white"))

    try:
        while True:
            user_input = get_multiline_input("\n> ")

            if user_input.lower() == "quit":
                if RICH_AVAILABLE:
                    console.print(
                        "\n[bold yellow]Thank you for using Lyne. Goodbye![/bold yellow]")
                else:
                    print(get_colored_text(
                        "\nThank you for using Lyne. Goodbye!", "yellow"))
                break

            if user_input.lower() == "/model":
                new_model = handle_model_selection(model_manager, chat_menu)
                if new_model:
                    try:
                        new_adapter = model_manager.create_adapter_for_model(
                            new_model)
                        if new_adapter and agent.switch_llm_adapter(new_adapter, new_model):
                            display_name = format_model_name(new_model)
                            if RICH_AVAILABLE:
                                console.print(
                                    f"🔄 [bold green]Switched to model: {display_name}[/bold green]")
                            else:
                                print(get_colored_text(
                                    f"🔄 Switched to model: {display_name}", "green"))
                            model_manager.set_preferred_model(new_model)
                        else:
                            if RICH_AVAILABLE:
                                console.print(Panel(
                                    f"[bold red]Failed to switch to model: {new_model}[/bold red]",
                                    title="[bold red]Model Switch Failed[/bold red]",
                                    border_style="red",
                                    padding=(1, 2)
                                ))
                            else:
                                print(get_colored_text(
                                    f"Failed to switch to model: {new_model}", "red"))
                    except Exception as e:
                        if RICH_AVAILABLE:
                            console.print(
                                Panel(
                                    f"[bold red]Error switching model: {str(e)}[/bold red]",
                                    title="[bold red]Model Switch Error[/bold red]",
                                    border_style="red",
                                    padding=(1, 2)
                                ))
                        else:
                            print(get_colored_text(
                                f"Error switching model: {str(e)}", "red"))
                continue

            if user_input.lower().startswith("/switch "):
                model_name = user_input[8:].strip()
                if model_name:
                    validation = model_manager.validate_model_availability(
                        model_name)
                    if validation.get("available", False):
                        try:
                            new_adapter = model_manager.create_adapter_for_model(
                                model_name)
                            if new_adapter and agent.switch_llm_adapter(new_adapter, model_name):
                                display_name = format_model_name(model_name)
                                if RICH_AVAILABLE:
                                    console.print(
                                        f"🔄 [bold green]Switched to model: {display_name}[/bold green]")
                                else:
                                    print(get_colored_text(
                                        f"🔄 Switched to model: {display_name}", "green"))
                                model_manager.set_preferred_model(model_name)
                            else:
                                if RICH_AVAILABLE:
                                    console.print(
                                        Panel(
                                            f"[bold red]Failed to switch to model: {model_name}[/bold red]",
                                            title="[bold red]Model Switch Failed[/bold red]",
                                            border_style="red",
                                            padding=(1, 2)
                                        ))
                                else:
                                    print(get_colored_text(
                                        f"Failed to switch to model: {model_name}", "red"))
                        except Exception as e:
                            if RICH_AVAILABLE:
                                console.print(
                                    Panel(
                                        f"[bold red]Error switching model: {str(e)}[/bold red]",
                                        title="[bold red]Model Switch Error[/bold red]",
                                        border_style="red",
                                        padding=(1, 2)
                                    ))
                            else:
                                print(get_colored_text(
                                    f"Error switching model: {str(e)}", "red"))
                    else:
                        error_msg = validation.get(
                            "error", "Model not available")
                        if RICH_AVAILABLE:
                            console.print(Panel(
                                f"[bold red]Cannot switch to model: {model_name}[/bold red]\n\n"
                                f"[yellow]{error_msg}[/yellow]\n\n"
                                "Please use the API Configuration menu to set up your keys.",
                                title="[bold red]Model Unavailable[/bold red]",
                                border_style="red",
                                padding=(1, 2)
                            ))
                        else:
                            print(get_colored_text(
                                f"Cannot switch to model: {model_name}", "red"))
                            print(get_colored_text(error_msg, "yellow"))
                else:
                    if RICH_AVAILABLE:
                        console.print(Panel(
                            f"[bold red]Please specify a model name. Usage: /switch <model_name>[/bold red]",
                            title="[bold red]Invalid Command[/bold red]",
                            border_style="red",
                            padding=(1, 2)
                        ))
                    else:
                        print(get_colored_text(
                            "Please specify a model name. Usage: /switch <model_name>", "red"))
                continue

            if user_input.lower() == "/menu":
                nav_context = NavigationContext()
                nav_context.save_conversation_context(
                    agent, conversation_id, current_path)

                display_navigation_menu()
                choice = get_navigation_choice()

                if choice == 1:
                    if RICH_AVAILABLE:
                        console.print(
                            "🏠 [bold cyan]Returning to main menu...[/bold cyan]")
                    else:
                        print("Returning to main menu...")

                    nav_context.save_conversation_context(
                        agent, conversation_id, current_path)

                    chat_menu = ChatMenu(project_path=current_path)
                    new_conversation_id, new_selected_model = chat_menu.run_menu(
                        model_manager)

                    if new_conversation_id == "":
                        return

                    if new_conversation_id and new_conversation_id != conversation_id:
                        conversation_id = new_conversation_id
                        agent = setup_agent(
                            current_path, model_manager, new_selected_model, conversation_id)

                        if new_selected_model:
                            display_name = format_model_name(
                                new_selected_model)
                            if RICH_AVAILABLE:
                                console.print(
                                    f"✅ [bold green]Ready with model: {display_name}[/bold green]")
                            else:
                                print(get_colored_text(
                                    f"Ready with model: {display_name}", "green"))

                    if RICH_AVAILABLE:
                        console.print(
                            "✅ [bold green]Returned to conversation[/bold green]")
                    else:
                        print("Returned to conversation")

                elif choice == 2:
                    if RICH_AVAILABLE:
                        console.print(
                            "💬 [bold cyan]Switching conversations...[/bold cyan]")
                    else:
                        print("Switching conversations...")

                    nav_context.save_conversation_context(
                        agent, conversation_id, current_path)

                    chat_menu = ChatMenu(project_path=current_path)
                    conversations = chat_menu.conversation_history.get_recent_conversations(
                        limit=10, project_path=current_path)

                    new_conversation_id = chat_menu._run_chat_menu(
                        conversations)

                    if new_conversation_id and new_conversation_id != conversation_id:
                        conversation_id = new_conversation_id
                        agent = setup_agent(current_path, model_manager, getattr(
                            agent, 'current_model', None), conversation_id)

                        if RICH_AVAILABLE:
                            console.print(
                                "✅ [bold green]Switched conversations[/bold green]")
                        else:
                            print("Switched conversations")
                    else:
                        if RICH_AVAILABLE:
                            console.print(
                                "✅ [bold green]Stayed in current conversation[/bold green]")
                        else:
                            print("Stayed in current conversation")

                elif choice == 3:
                    if RICH_AVAILABLE:
                        console.print(
                            "⚙️ [bold cyan]Opening model settings...[/bold cyan]")
                    else:
                        print("Opening model settings...")

                    nav_context.save_conversation_context(
                        agent, conversation_id, current_path)

                    new_model = handle_model_selection(
                        model_manager, chat_menu)
                    if new_model:
                        try:
                            new_adapter = model_manager.create_adapter_for_model(
                                new_model)
                            if new_adapter and agent.switch_llm_adapter(new_adapter, new_model):
                                display_name = format_model_name(new_model)
                                if RICH_AVAILABLE:
                                    console.print(
                                        f"🔄 [bold green]Switched to model: {display_name}[/bold green]")
                                else:
                                    print(get_colored_text(
                                        f"🔄 Switched to model: {display_name}", "green"))
                                model_manager.set_preferred_model(new_model)
                            else:
                                if RICH_AVAILABLE:
                                    console.print(
                                        f"❌ [bold red]Failed to switch to model: {new_model}[/bold red]")
                                else:
                                    print(get_colored_text(
                                        f"Failed to switch to model: {new_model}", "red"))
                        except Exception as e:
                            if RICH_AVAILABLE:
                                console.print(
                                    Panel(
                                        f"[bold red]Error switching model: {str(e)}[/bold red]",
                                        title="[bold red]Model Switch Error[/bold red]",
                                        border_style="red",
                                        padding=(1, 2)
                                    ))
                            else:
                                print(get_colored_text(
                                    f"Error switching model: {str(e)}", "red"))

                    if RICH_AVAILABLE:
                        console.print(
                            "✅ [bold green]Returned to conversation[/bold green]")
                    else:
                        print("Returned to conversation")

                elif choice == 4:
                    display_help_menu()

                elif choice == 5:

                    try:
                        from vcs.version_control import VersionControl
                        vcs = VersionControl(current_path)
                        vcs.run_menu()
                    except ImportError as e:
                        if RICH_AVAILABLE:
                            console.print(Panel(
                                f"[bold red]Version Control System not available: {str(e)}[/bold red]\n\n"
                                "The VCS module may not be properly installed.",
                                title="[bold red]VCS Error[/bold red]",
                                border_style="red",
                                padding=(1, 2)
                            ))
                        else:
                            print(f"VCS Error: {str(e)}")
                    except Exception as e:
                        if RICH_AVAILABLE:
                            console.print(Panel(
                                f"[bold red]Error starting VCS: {str(e)}[/bold red]",
                                title="[bold red]VCS Error[/bold red]",
                                border_style="red",
                                padding=(1, 2)
                            ))
                        else:
                            print(f"VCS Error: {str(e)}")

                elif choice == 6:

                    if RICH_AVAILABLE:
                        console.print(
                            "🔑 [bold cyan]Opening API Configuration...[/bold cyan]")
                    else:
                        print("Opening API Configuration...")

                    try:
                        from api_config_menu import APIConfigMenu
                        api_menu = APIConfigMenu()
                        api_menu.run_menu()
                    except ImportError as e:
                        if RICH_AVAILABLE:
                            console.print(Panel(
                                f"[bold red]API Configuration not available: {str(e)}[/bold red]\n\n"
                                "The API configuration module may not be properly installed.",
                                title="[bold red]API Config Error[/bold red]",
                                border_style="red",
                                padding=(1, 2)
                            ))
                        else:
                            print(f"API Config Error: {str(e)}")
                    except Exception as e:
                        if RICH_AVAILABLE:
                            console.print(Panel(
                                f"[bold red]Error opening API configuration: {str(e)}[/bold red]",
                                title="[bold red]API Config Error[/bold red]",
                                border_style="red",
                                padding=(1, 2)
                            ))
                        else:
                            print(f"API Config Error: {str(e)}")

                elif choice == 7:
                    if RICH_AVAILABLE:
                        console.print(
                            "✅ [bold green]Staying in conversation[/bold green]")
                    else:
                        print("Staying in conversation")

                continue

            if user_input.lower() == "/help":
                display_help_menu()
                continue

            if user_input.lower() == "/back":
                if RICH_AVAILABLE:
                    console.print(
                        "🏠 [bold cyan]Going to main menu...[/bold cyan]")
                else:
                    print("Going to main menu...")

                nav_context = NavigationContext()
                nav_context.save_conversation_context(
                    agent, conversation_id, current_path)

                chat_menu = ChatMenu(project_path=current_path)
                new_conversation_id, new_selected_model = chat_menu.run_menu(
                    model_manager)

                if new_conversation_id == "":
                    return

                if new_conversation_id and new_conversation_id != conversation_id:
                    conversation_id = new_conversation_id
                    agent = setup_agent(
                        current_path, model_manager, new_selected_model, conversation_id)

                    if new_selected_model:
                        display_name = format_model_name(new_selected_model)
                        if RICH_AVAILABLE:
                            console.print(
                                f"✅ [bold green]Ready with model: {display_name}[/bold green]")
                        else:
                            print(get_colored_text(
                                f"Ready with model: {display_name}", "green"))

                if RICH_AVAILABLE:
                    console.print(
                        "✅ [bold green]Returned to conversation[/bold green]")
                else:
                    print("Returned to conversation")

                continue

            if user_input.lower() == "/chats":
                if RICH_AVAILABLE:
                    console.print(
                        "💬 [bold cyan]Switching conversations...[/bold cyan]")
                else:
                    print("Switching conversations...")

                nav_context = NavigationContext()
                nav_context.save_conversation_context(
                    agent, conversation_id, current_path)

                chat_menu = ChatMenu(project_path=current_path)
                conversations = chat_menu.conversation_history.get_recent_conversations(
                    limit=10, project_path=current_path)

                new_conversation_id = chat_menu._run_chat_menu(conversations)

                if new_conversation_id and new_conversation_id != conversation_id:
                    conversation_id = new_conversation_id
                    agent = setup_agent(current_path, model_manager, getattr(
                        agent, 'current_model', None), conversation_id)

                    if RICH_AVAILABLE:
                        console.print(
                            "✅ [bold green]Switched conversations[/bold green]")
                    else:
                        print("Switched conversations")
                else:
                    if RICH_AVAILABLE:
                        console.print(
                            "✅ [bold green]Stayed in current conversation[/bold green]")
                    else:
                        print("Stayed in current conversation")

                continue

            if not user_input:
                continue

            try:
                processed_query = user_input
                idx = FileSystemIndexer(current_path)
                loaded = idx.load_index()

                token_pattern = r"/(file|folder):([^\s]+)"
                tokens = re.findall(
                    token_pattern, processed_query, flags=re.IGNORECASE)
                if tokens:
                    tokens = [tokens[0]]

                for ttype, term in tokens:
                    is_file = ttype.lower() == "file"
                    candidates = idx.fuzzy_find_files(
                        term, limit=5) if is_file else idx.fuzzy_find_folders(term, limit=5)

                    selection = None
                    if candidates:
                        if RICH_AVAILABLE:
                            table = Table(show_header=True, header_style="bold cyan",
                                          border_style="blue", show_lines=True, expand=True)
                            table.add_column(
                                "#", justify="right", style="white")
                            table.add_column("Name", style="white")
                            table.add_column("Path", style="white")
                            for i, c in enumerate(candidates, 1):
                                table.add_row(str(i), c.get(
                                    "name", ""), c.get("path", ""))
                            console.print(Panel(
                                table, title="Select attachment (enter number) or 0 to skip", border_style="green", padding=(1, 2)))
                            choice_str = console.input(
                                Text("Choice: ", style="bold cyan")).strip()
                        else:
                            print("Top matches:")
                            for i, c in enumerate(candidates, 1):
                                print(
                                    f"{i}. {c.get('name', '')} - {c.get('path', '')}")
                            choice_str = input("Choice (0 to skip): ").strip()

                        try:
                            choice = int(choice_str)
                        except Exception:
                            choice = 0

                        if 1 <= choice <= len(candidates):
                            selection = candidates[choice - 1]

                    token_full = f"/{ttype}:{term}"
                    if selection:
                        sel_name = selection.get("name", "")
                        if is_file and "." in sel_name:
                            sel_name = os.path.splitext(sel_name)[0]
                        processed_query = processed_query.replace(
                            token_full, sel_name)
                        try:
                            from conversation_history import ConversationHistory
                            ch = ConversationHistory()
                            ch.add_attachment(conversation_id, "file" if is_file else "folder", selection.get(
                                "path", ""), selection.get("name", ""))
                        except Exception:
                            pass
                    else:
                        processed_query = processed_query.replace(
                            token_full, "")

                if processed_query.strip().lower() == "/attachments":
                    from conversation_history import ConversationHistory
                    ch = ConversationHistory()
                    atts = ch.get_attachments(conversation_id)
                    if RICH_AVAILABLE:
                        if atts:
                            table = Table(show_header=True, header_style="bold cyan",
                                          border_style="blue", show_lines=True, expand=True)
                            table.add_column(
                                "#", justify="right", style="white")
                            table.add_column("Type", style="white")
                            table.add_column("Name", style="white")
                            table.add_column("Path", style="white")
                            for i, a in enumerate(atts, 1):
                                table.add_row(str(i), a.get("type", ""), a.get(
                                    "name", ""), a.get("path", ""))
                            console.print(
                                Panel(table, title="Current attachments", border_style="green", padding=(1, 2)))
                        else:
                            console.print(
                                Panel("No attachments.", border_style="yellow"))
                    else:
                        if atts:
                            print("Attachments:")
                            for i, a in enumerate(atts, 1):
                                print(
                                    f"{i}. {a.get('type', '')} - {a.get('name', '')} - {a.get('path', '')}")
                        else:
                            print("No attachments.")
                    continue

                if processed_query.strip().lower().startswith("/detach "):
                    term = processed_query.strip()[8:].strip()
                    from conversation_history import ConversationHistory
                    ch = ConversationHistory()
                    if term.lower() == "all":
                        ch.clear_attachments(conversation_id)
                        if RICH_AVAILABLE:
                            console.print(
                                Panel("Cleared all attachments.", border_style="green"))
                        else:
                            print("Cleared all attachments.")
                    else:
                        atts = ch.get_attachments(conversation_id)
                        if not atts:
                            if RICH_AVAILABLE:
                                console.print(
                                    Panel("No attachments to detach.", border_style="yellow"))
                            else:
                                print("No attachments to detach.")
                            continue
                        import difflib as _dl
                        names = [a.get("name", "") for a in atts]
                        scores = {}
                        t = term.lower()
                        for n in names:
                            nl = n.lower()
                            s = 0.0
                            if t in nl:
                                s = 1.0 - (nl.find(t) / max(1, len(nl)))
                                s += 0.5
                            else:
                                s = _dl.SequenceMatcher(a=t, b=nl).ratio()
                            scores[n] = max(scores.get(n, 0.0), s)
                        ranked = sorted(
                            scores.items(), key=lambda x: x[1], reverse=True)
                        ordered = []
                        for name, _ in ranked:
                            for a in atts:
                                if a.get("name", "") == name:
                                    ordered.append(a)
                        if ordered:
                            if RICH_AVAILABLE:
                                table = Table(show_header=True, header_style="bold cyan",
                                              border_style="blue", show_lines=True, expand=True)
                                table.add_column(
                                    "#", justify="right", style="white")
                                table.add_column("Type", style="white")
                                table.add_column("Name", style="white")
                                table.add_column("Path", style="white")
                                for i, a in enumerate(ordered[:5], 1):
                                    table.add_row(str(i), a.get("type", ""), a.get(
                                        "name", ""), a.get("path", ""))
                                console.print(Panel(
                                    table, title="Select to detach (enter number) or 0 to cancel", border_style="green", padding=(1, 2)))
                                choice_str = console.input(
                                    Text("Choice: ", style="bold cyan")).strip()
                            else:
                                print("Matches:")
                                for i, a in enumerate(ordered[:5], 1):
                                    print(
                                        f"{i}. {a.get('type', '')} - {a.get('name', '')} - {a.get('path', '')}")
                                choice_str = input(
                                    "Choice (0 to cancel): ").strip()
                            try:
                                choice = int(choice_str)
                            except Exception:
                                choice = 0
                            if 1 <= choice <= min(5, len(ordered)):
                                target = ordered[choice-1]
                                ch.remove_attachment(
                                    conversation_id, target.get("path", ""))
                                if RICH_AVAILABLE:
                                    console.print(
                                        Panel("Detached.", border_style="green"))
                                else:
                                    print("Detached.")
                        else:
                            if RICH_AVAILABLE:
                                console.print(
                                    Panel("No matching attachments found.", border_style="yellow"))
                            else:
                                print("No matching attachments found.")
                    continue

                if RICH_AVAILABLE:
                    header = Text("Sending query:", style="bold cyan")
                    console.print(header)
                    console.print(
                        Panel(Text(processed_query), border_style="cyan"))
                else:
                    print("Sending query:")
                    print(processed_query)
                result = run_query(agent, processed_query)
            except Exception as _e:
                result = run_query(agent, user_input)
            format_agent_response(result)

            try:
                if RICH_AVAILABLE:
                    from conversation_history import ConversationHistory
                    ch = ConversationHistory()
                    atts = ch.get_attachments(conversation_id)
                    if atts:
                        table = Table(show_header=True, header_style="bold cyan",
                                      border_style="blue", show_lines=True, expand=False)
                        table.add_column("Type", style="white")
                        table.add_column("Name", style="white")
                        for a in atts[-5:]:
                            table.add_row(a.get("type", ""), a.get("name", ""))
                        console.print(Panel.fit(
                            table, title=f"Attachments ({len(atts)})", border_style="green", padding=(0, 1)))
                else:
                    from conversation_history import ConversationHistory
                    ch = ConversationHistory()
                    atts = ch.get_attachments(conversation_id)
                    if atts:
                        print(
                            f"Attachments ({len(atts)}): " + ", ".join([a.get('name', '') for a in atts[-5:]]))
            except Exception:
                pass

    except KeyboardInterrupt:
        if RICH_AVAILABLE:
            console.print(
                "\n\n[bold yellow]Interrupted by user. Exiting...[/bold yellow]")
        else:
            print(get_colored_text("\n\nInterrupted by user. Exiting...", "yellow"))
    except Exception as e:
        if RICH_AVAILABLE:
            console.print(Panel(
                f"[bold red]An unexpected error occurred: {e}[/bold red]", border_style="red"))
        else:
            print(get_colored_text(
                f"\n[Error] An unexpected error occurred: {str(e)}", "red"))


if __name__ == "__main__":
    main()
