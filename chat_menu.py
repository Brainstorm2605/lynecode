"""
Chat Menu System for Lyne

Provides a user interface for selecting conversations and models.
"""

from typing import Optional, List, Dict, Tuple
from datetime import datetime
from pathlib import Path
from conversation_history import ConversationHistory
from rich.console import Console
from rich.panel import Panel
from rich.text import Text


class ChatMenu:
    """Handles chat selection and conversation management UI."""

    def __init__(self, project_path: Optional[str] = None):
        """Initialize chat menu with conversation history."""
        self.conversation_history = ConversationHistory()
        self.console = Console()
        self.project_path = project_path

    def display_main_menu(self) -> None:
        """Display the main menu with Chat, Model Selection, API Config, and Version Control options."""
        menu_text = Text()
        menu_text.append("1. 💬 Start Chat\n", style="bold green")
        menu_text.append("2. ⚙️  Model Selection\n", style="bold blue")
        menu_text.append("3. 🔑 API Configuration\n", style="bold yellow")
        menu_text.append("4. 🔄 Version Control\n", style="bold magenta")
        menu_text.append("5. ❌ Exit Lyne\n", style="bold red")

        self.console.print(Panel(
            menu_text,
            title="🤖 LYNE CODE - MAIN MENU",
            border_style="cyan",
            title_align="center",
            padding=(1, 2)
        ))

    def display_model_menu(self, all_models: List[str], model_validations: Dict[str, Dict]) -> None:
        """Display the model selection menu with all models from MODEL_LIST."""
        menu_text = Text()
        menu_text.append("Select a Model:\n\n", style="bold cyan")

        for i, model in enumerate(all_models, 1):
            validation = model_validations.get(model, {})

            display_name = model
            if "-thinking" in model:
                display_name = model.replace("-thinking", " 🧠")

            if validation.get("available", False):
                menu_text.append(
                    f"{i}. ✅ {display_name} ({validation.get('provider', 'unknown')})\n", style="green")
            else:
                menu_text.append(
                    f"{i}. ⚠️  {display_name} (API key required)\n", style="yellow")

        menu_text.append(
            f"\n{len(all_models) + 1}. 🔙 Back to Main Menu\n", style="bold yellow")

        self.console.print(Panel(
            menu_text,
            title="🤖 LYNE CODE - MODEL SELECTION",
            border_style="blue",
            title_align="center",
            padding=(1, 2)
        ))

    def display_chat_menu(self, conversations: List[Dict]) -> None:
        """Display the chat selection menu."""
        menu_text = Text()
        menu_text.append("0. 🆕 Create New Conversation\n", style="bold green")
        menu_text.append("1. 🔙 Back to Main Menu\n", style="bold yellow")

        if conversations:
            if self.project_path:
                menu_text.append(f"\n📜 Conversations for {Path(self.project_path).name}:\n",
                                 style="bold cyan")
            else:
                menu_text.append("\n📜 Previous Conversations:\n",
                                 style="bold cyan")
            for i, conv in enumerate(conversations, 2):
                title_display = self.conversation_history.format_conversation_title(
                    conv)
                menu_text.append(f"{i}. {title_display}\n", style="white")

        title_text = "🤖 LYNE CODE - CHAT MENU"
        if self.project_path:
            title_text += f" ({Path(self.project_path).name})"

        self.console.print(Panel(
            menu_text,
            title=title_text,
            border_style="cyan",
            title_align="center",
            padding=(1, 2)
        ))

        if not conversations:
            if self.project_path:
                self.console.print(
                    Panel(
                        f"📝 No conversations found for {Path(self.project_path).name}. A new one will be created for you.",
                        title="[bold yellow]Notice[/bold yellow]",
                        border_style="yellow",
                        padding=(1, 2)
                    )
                )
            else:
                self.console.print(
                    Panel(
                        "📝 No previous conversations found. A new one will be created for you.",
                        title="[bold yellow]Notice[/bold yellow]",
                        border_style="yellow",
                        padding=(1, 2)
                    )
                )

    def get_user_choice(self, max_choice: int, prompt: str = "Select an option") -> int:
        """Get user selection from menu."""
        while True:
            try:
                choice_str = self.console.input(
                    f"\n👤 [bold cyan]{prompt}:[/bold cyan] ").strip()
                if not choice_str:
                    continue

                choice_num = int(choice_str)
                if 0 <= choice_num <= max_choice:
                    return choice_num
                else:
                    self.console.print(
                        f"❌ [bold red]Please enter a number between 0 and {max_choice}.[/bold red]")

            except ValueError:
                self.console.print(
                    "❌ [bold red]Please enter a valid number.[/bold red]")
            except KeyboardInterrupt:
                self.console.print("\n\n👋 [bold yellow]Goodbye![/bold yellow]")
                return 1

    def get_main_menu_choice(self) -> int:
        """Get user choice from main menu."""
        return self.get_user_choice(5, "Select an option")

    def get_model_choice(self, all_models: List[str]) -> Tuple[int, bool]:
        """Get user choice from model menu. Returns (choice, is_back_option)."""
        max_choice = len(all_models) + 1
        prompt = f"Select a model (1-{len(all_models)}=select model, {max_choice}=back)"
        choice = self.get_user_choice(max_choice, prompt)

        if choice == max_choice:
            return choice, True
        else:
            return choice, False

    def create_new_conversation_title(self) -> str:
        """Prompt user for a conversation title."""
        self.console.print(
            "\n📝 [bold green]Creating new conversation...[/bold green]")
        while True:
            title = self.console.input(
                "   [cyan]Enter conversation title (or press Enter for auto-generated):[/cyan] ").strip()
            if not title:
                title = f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                self.console.print(
                    f"   [yellow]Auto-generated title: {title}[/yellow]")
                return title
            elif len(title) > 100:
                self.console.print(
                    "❌ [bold red]Title too long. Please keep it under 100 characters.[/bold red]")
            else:
                return title

    def show_conversation_preview(self, conversation_id: str) -> None:
        """Show a preview of the selected conversation."""
        conversation = self.conversation_history.get_conversation(
            conversation_id)
        if not conversation:
            return

        messages = conversation.get("messages", [])
        if not messages:
            self.console.print(
                Panel("[bold yellow]This conversation has no messages yet.[/bold yellow]",
                      title="📝 Preview", border_style="yellow")
            )
            return

        preview_text = ""
        recent_messages = messages[-3:]
        for msg in recent_messages:
            timestamp = datetime.fromisoformat(
                msg['timestamp']).strftime("%H:%M")
            query = msg['query'][:60] + \
                '...' if len(msg['query']) > 60 else msg['query']
            response = msg['response'][:80] + \
                '...' if len(msg['response']) > 80 else msg['response']
            preview_text += f"[cyan][{timestamp}][/cyan] [bold]Query:[/bold] {query}\n"
            preview_text += f"[cyan][{timestamp}][/cyan] [bold]Response:[/bold] {response}\n\n"

        if len(messages) > 3:
            preview_text += f"[dim]... and {len(messages) - 3} earlier messages[/dim]\n[dim]Use 'e' to expand full history[/dim]"

        self.console.print(Panel(
            preview_text.strip(),
            title=f"📖 Conversation Preview: {conversation['title']}",
            border_style="blue",
            padding=(1, 2)
        ))

    def show_full_conversation_history(self, conversation_id: str) -> None:
        """Show the full conversation history with expand/collapse functionality."""
        conversation = self.conversation_history.get_conversation(
            conversation_id)
        if not conversation:
            return

        messages = conversation.get("messages", [])
        if not messages:
            self.console.print(
                Panel("[bold yellow]This conversation has no messages yet.[/bold yellow]",
                      title="📝 Full History", border_style="yellow")
            )
            return

        history_text = ""
        for i, msg in enumerate(messages, 1):
            timestamp = datetime.fromisoformat(
                msg['timestamp']).strftime("%Y-%m-%d %H:%M:%S")
            query = msg['query']
            response = msg['response']

            history_text += f"[bold cyan]#{i} [{timestamp}][/bold cyan]\n"
            history_text += f"[bold]Query:[/bold] {query}\n"
            history_text += f"[bold]Response:[/bold] {response}\n\n"

        self.console.print(Panel(
            history_text.strip(),
            title=f"📜 Full Conversation History: {conversation['title']}",
            border_style="green",
            padding=(1, 2),
            expand=False
        ))

    def run_menu(self, model_manager=None) -> Tuple[Optional[str], Optional[str]]:
        """
        Run the main menu system with chat and model selection.

        Args:
            model_manager: Optional model manager instance for model operations

        Returns:
            Tuple of (conversation_id, selected_model) where:
            - conversation_id: ID to continue with, or None for new conversation, or empty string to exit
            - selected_model: Selected model name, or None if not changed
        """
        try:
            conversations = self.conversation_history.get_recent_conversations(
                limit=10, project_path=self.project_path)
            current_model = None

            while True:
                self.display_main_menu()
                choice = self.get_main_menu_choice()

                if choice == 1:
                    result = self._run_chat_menu(conversations)
                    if result:
                        return result, current_model

                elif choice == 2:
                    if model_manager:
                        result = self._run_model_menu(model_manager)
                        if result:

                            validation = model_manager.validate_model_availability(
                                result)
                            if validation.get("available", False):
                                current_model = result

                                display_name = current_model
                                if "-thinking" in current_model:
                                    display_name = current_model.replace(
                                        "-thinking", " 🧠")
                                self.console.print(
                                    f"✅ [bold green]Selected model: {display_name}[/bold green]")
                                continue
                            else:

                                error_msg = validation.get(
                                    "error", "Model not available")
                                self.console.print(Panel(
                                    f"[bold red]Cannot select model: {result}[/bold red]\n\n"
                                    f"[yellow]{error_msg}[/yellow]\n\n"
                                    "Please use the API Configuration menu to set up your keys.",
                                    title="[bold red]Model Unavailable[/bold red]",
                                    border_style="red",
                                    padding=(1, 2)
                                ))
                                continue
                    else:
                        self.console.print(Panel(
                            "[bold red]Model manager not available[/bold red]",
                            title="[bold red]Model Manager Error[/bold red]",
                            border_style="red",
                            padding=(1, 2)
                        ))
                        continue

                elif choice == 3:

                    try:
                        from api_config_menu import APIConfigMenu
                        api_menu = APIConfigMenu()
                        api_menu.run_menu()
                        continue
                    except ImportError as e:
                        self.console.print(Panel(
                            f"[bold red]API Configuration not available: {str(e)}[/bold red]\n\n"
                            "The API configuration module may not be properly installed.",
                            title="[bold red]API Config Error[/bold red]",
                            border_style="red",
                            padding=(1, 2)
                        ))
                        continue
                    except Exception as e:
                        self.console.print(Panel(
                            f"[bold red]Error opening API configuration: {str(e)}[/bold red]",
                            title="[bold red]API Config Error[/bold red]",
                            border_style="red",
                            padding=(1, 2)
                        ))
                        continue

                elif choice == 4:

                    try:
                        from vcs.version_control import VersionControl
                        vcs = VersionControl(str(self.project_path))
                        vcs.run_menu()
                        continue
                    except ImportError as e:
                        self.console.print(Panel(
                            f"[bold red]Version Control System not available: {str(e)}[/bold red]\n\n"
                            "The VCS module may not be properly installed.",
                            title="[bold red]VCS Error[/bold red]",
                            border_style="red",
                            padding=(1, 2)
                        ))
                        continue
                    except Exception as e:
                        self.console.print(Panel(
                            f"[bold red]Error starting VCS: {str(e)}[/bold red]",
                            title="[bold red]VCS Error[/bold red]",
                            border_style="red",
                            padding=(1, 2)
                        ))
                        continue

                elif choice == 5:
                    return "", current_model

        except KeyboardInterrupt:
            self.console.print("\n\n👋 [bold yellow]Goodbye![/bold yellow]")
            return "", current_model
        except Exception as e:
            self.console.print(
                f"\n❌ [bold red]Error in main menu: {str(e)}[/bold red]")
            self.console.print(
                "   [yellow]Creating new conversation...[/yellow]")
            title = f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            return self.conversation_history.create_conversation(title), current_model

    def _run_chat_menu(self, conversations: List[Dict]) -> Optional[str]:
        """Run the chat selection submenu."""
        while True:
            self.display_chat_menu(conversations)

            if not conversations:
                title = self.create_new_conversation_title()
                conversation_id = self.conversation_history.create_conversation(
                    title, self.project_path)
                return conversation_id

            max_choice = len(conversations) + 1
            choice = self.get_user_choice(
                max_choice, "Select an option (0 = new, 1 = back, 2+ for chats)")

            if choice == 0:
                title = self.create_new_conversation_title()
                conversation_id = self.conversation_history.create_conversation(
                    title, self.project_path)
                return conversation_id

            elif choice == 1:
                return None

            elif 2 <= choice <= max_choice:
                selected_conv = conversations[choice - 2]
                conversation_id = selected_conv["id"]

                self.show_conversation_preview(conversation_id)

                while True:
                    action = self.console.input(
                        f"\n🔄 [bold]Continue with '{selected_conv['title']}'?[/bold] (y/n/e=expand): ").strip().lower()
                    if action in ['y', 'yes']:
                        return conversation_id
                    elif action in ['e', 'expand']:
                        self.show_full_conversation_history(conversation_id)
                        continue
                    elif action in ['n', 'no']:
                        break

    def _run_model_menu(self, model_manager) -> Optional[str]:
        """Run the model selection submenu."""
        try:

            all_models = model_manager.get_all_models_from_list()

            model_validations = {}
            for model in all_models:
                validation = model_manager.validate_model_availability(model)
                model_validations[model] = validation

            while True:
                self.display_model_menu(all_models, model_validations)
                choice, is_back = self.get_model_choice(all_models)

                if is_back:
                    return None
                else:
                    selected_model = all_models[choice - 1]
                    validation = model_validations[selected_model]

                    if validation.get("available", False):
                        return selected_model
                    else:
                        error_msg = validation.get(
                            "error", "Model not available")
                        self.console.print(Panel(
                            f"[bold red]Cannot select model: {selected_model}[/bold red]\n\n"
                            f"[yellow]{error_msg}[/yellow]\n\n"
                            "Please use the API Configuration menu to set up your API keys.",
                            title="[bold red]Model Unavailable[/bold red]",
                            border_style="red",
                            padding=(1, 2)
                        ))
                        continue

        except Exception as e:
            self.console.print(
                f"❌ [bold red]Error in model selection: {str(e)}[/bold red]")
            return None

    def display_inline_model_menu(self, all_models: List[str], model_validations: Dict[str, Dict], current_model: Optional[str] = None) -> None:
        """Display inline model selection menu for conversation switching."""
        menu_text = Text()
        menu_text.append("🔄 Available Models:\n\n", style="bold cyan")

        for i, model in enumerate(all_models, 1):
            validation = model_validations.get(model, {})

            display_name = model
            if "-thinking" in model:
                display_name = model.replace("-thinking", " 🧠")

            if model == current_model:
                menu_text.append(
                    f"● {i}. 🟢 {display_name} (current)\n", style="bold green")
            elif validation.get("available", False):
                menu_text.append(
                    f"○ {i}. ✅ {display_name}\n", style="green")
            else:
                menu_text.append(
                    f"○ {i}. ⚠️  {display_name} (API key required)\n", style="yellow")

        menu_text.append(
            f"\n○ {len(all_models) + 1}. ❌ Cancel\n", style="bold yellow")

        self.console.print(Panel(
            menu_text,
            title="🔄 MODEL SELECTION",
            border_style="blue",
            title_align="center",
            padding=(1, 2)
        ))

    def handle_inline_model_selection(self, model_manager, current_model=None) -> Optional[str]:
        """Handle inline model selection during conversation."""
        try:
            all_models = model_manager.get_all_models_from_list()

            model_validations = {}
            for model in all_models:
                validation = model_manager.validate_model_availability(model)
                model_validations[model] = validation

            while True:
                self.display_inline_model_menu(
                    all_models, model_validations, current_model)
                prompt = Text("Select model (1-" + str(len(all_models)) + " or " +
                              str(len(all_models) + 1) + "=cancel): ", style="bold cyan")
                choice_str = self.console.input(prompt).strip()

                if not choice_str:
                    continue

                try:
                    choice_num = int(choice_str)
                    if choice_num == len(all_models) + 1:
                        return None

                    if 1 <= choice_num <= len(all_models):
                        selected_model = all_models[choice_num - 1]
                        validation = model_validations[selected_model]

                        if validation.get("available", False):
                            return selected_model
                        else:
                            error_msg = validation.get(
                                "error", "Model not available")
                            self.console.print(Panel(
                                f"[bold red]Cannot select model: {selected_model}[/bold red]\n\n"
                                f"[yellow]{error_msg}[/yellow]\n\n"
                                "Please use the API Configuration menu to set up your API keys.",
                                title="[bold red]Model Unavailable[/bold red]",
                                border_style="red",
                                padding=(1, 2)
                            ))
                            continue
                    else:
                        self.console.print(
                            f"❌ [bold red]Please enter a number between 1 and {len(all_models) + 1}.[/bold red]")

                except ValueError:
                    self.console.print(
                        "❌ [bold red]Please enter a valid number.[/bold red]")

        except Exception as e:
            self.console.print(
                f"❌ [bold red]Error in inline model selection: {str(e)}[/bold red]")
            return None
