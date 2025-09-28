#!/usr/bin/env python3
"""
API Configuration Menu for Lyne

Secure API key management system with menu driven interface.
Stores configuration securely in user's home directory.
"""

import json
import os
from pathlib import Path
from typing import Dict, Optional

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    from rich.prompt import Prompt, Confirm
    RICH_AVAILABLE = True
    console = Console()
except ImportError:
    RICH_AVAILABLE = False


class SecureConfigManager:
    """Secure configuration manager for API keys and settings."""

    def __init__(self):
        """Initialize secure config manager."""
        self.config_dir = Path.home() / ".lynecode"
        self.config_file = self.config_dir / "config.json"
        self._ensure_config_dir()
        self._set_secure_permissions()

    def _ensure_config_dir(self):
        """Create config directory if it doesn't exist."""
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def _set_secure_permissions(self):
        """Set secure file permissions on config directory."""
        try:

            if os.name != 'nt':
                self.config_dir.chmod(0o700)
                if self.config_file.exists():
                    self.config_file.chmod(0o600)
        except Exception:

            pass

    def set_key(self, key: str, value: str):
        """Set a configuration key."""
        config = self._load_config()
        config[key] = value
        self._save_config(config)

    def get_key(self, key: str) -> Optional[str]:
        """Get a configuration key."""
        config = self._load_config()
        return config.get(key)

    def delete_key(self, key: str):
        """Delete a configuration key."""
        config = self._load_config()
        if key in config:
            del config[key]
            self._save_config(config)

    def list_keys(self) -> Dict[str, str]:
        """List all configuration keys with masked sensitive values."""
        config = self._load_config()
        masked = {}
        sensitive_keywords = ['key', 'token', 'secret', 'password']

        for key, value in config.items():
            if any(keyword in key.lower() for keyword in sensitive_keywords):
                masked[key] = self._mask_value(str(value))
            else:
                masked[key] = str(value)
        return masked

    def clear_all(self):
        """Clear all configuration."""
        self._save_config({})

    def _load_config(self) -> Dict[str, str]:
        """Load configuration from file."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_config(self, config: Dict[str, str]):
        """Save configuration to file."""
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=2)
        self._set_secure_permissions()

    def _mask_value(self, value: str) -> str:
        """Mask sensitive values for display."""
        if len(value) <= 8:
            return "*" * len(value)
        return value[:4] + "*" * (len(value) - 8) + value[-4:]


class APIConfigMenu:
    """Menu-driven interface for API configuration."""

    def __init__(self):
        """Initialize API config menu."""
        self.config_manager = SecureConfigManager()

    def run_menu(self):
        """Run the API configuration menu with improved UX."""
        self._show_welcome()

        try:
            while True:
                self._display_menu()
                choice = self._get_choice()

                self._clear_screen()

                if choice == 1:
                    self._handle_openai_setup()
                elif choice == 2:
                    self._handle_gemini_setup()
                elif choice == 3:
                    self._handle_azure_setup()
                elif choice == 4:
                    self._handle_view_config()
                elif choice == 5:
                    self._handle_delete_key()
                elif choice == 6:
                    self._handle_clear_all()
                elif choice == 7:
                    self._show_message("🔙 Returning to main menu...")
                    break
                else:
                    self._show_error("Invalid choice. Please select 1-7.")
                    continue

                if choice != 7:
                    self._ask_next_action()

        except KeyboardInterrupt:
            self._show_message("\n🔙 Returning to main menu...")
            return
        except Exception as e:
            self._show_error(f"Unexpected error: {e}")
            return

    def _display_menu(self):
        """Display the API configuration menu."""
        menu_text = Text()
        menu_text.append("🔑 API CONFIGURATION MENU\n\n", style="bold cyan")
        menu_text.append("Choose an option:\n\n", style="white")
        menu_text.append("1. 🔑 Set OpenAI API Key\n", style="green")
        menu_text.append("2. 💎 Set Gemini API Key\n", style="blue")
        menu_text.append("3. ☁️  Set Azure Configuration\n", style="magenta")
        menu_text.append("4. 👁️  View Current Configuration\n", style="cyan")
        menu_text.append("5. 🗑️  Delete Specific Key\n", style="red")
        menu_text.append("6. 🧹 Clear All Configuration\n", style="red bold")
        menu_text.append("7. 🔙 Back to Main Menu\n", style="yellow")

        if RICH_AVAILABLE:
            console.print(Panel(
                menu_text,
                title="🔐 SECURE API CONFIGURATION",
                border_style="cyan",
                title_align="center",
                padding=(1, 2)
            ))
        else:
            print("\n" + "="*50)
            print("🔐 SECURE API CONFIGURATION")
            print("="*50)
            print("1. 🔑 Set OpenAI API Key")
            print("2. 💎 Set Gemini API Key")
            print("3. ☁️  Set Azure Configuration")
            print("4. 👁️  View Current Configuration")
            print("5. 🗑️  Delete Specific Key")
            print("6. 🧹 Clear All Configuration")
            print("7. 🔙 Back to Main Menu")
            print("="*50)

    def _show_welcome(self):
        """Show welcome message."""
        welcome_msg = Text()
        welcome_msg.append(
            "🔐 Welcome to Secure API Configuration!\n\n", style="bold cyan")
        welcome_msg.append(
            "Your API keys are stored securely and can only be managed through this menu.\n", style="white")
        welcome_msg.append(
            "Keys are automatically masked for security.\n\n", style="dim white")
        welcome_msg.append(
            "💡 Tip: You can also access this from '/menu' → option 6 during conversations.", style="italic yellow")

        if RICH_AVAILABLE:
            console.print(Panel(
                welcome_msg,
                title="🔑 LYNE API CONFIGURATION",
                border_style="green",
                title_align="center",
                padding=(1, 2)
            ))
        else:
            print("\n" + "="*60)
            print("🔑 LYNE API CONFIGURATION")
            print("="*60)
            print("Welcome to Secure API Configuration!")
            print(
                "Your API keys are stored securely and can only be managed through this menu.")
            print("Keys are automatically masked for security.")
            print(
                "\n💡 Tip: You can also access this from '/menu' → option 6 during conversations.")
            print("="*60)

        input("\nPress Enter to continue...")

    def _clear_screen(self):
        """Clear the screen for better UX (optional)."""
        try:
            if RICH_AVAILABLE:
                console.clear()
            else:

                os.system('cls' if os.name == 'nt' else 'clear')
        except:
            pass

    def _handle_openai_setup(self):
        """Handle OpenAI API key setup with clear flow."""
        if RICH_AVAILABLE:
            console.print("\n[bold green]🔑 OpenAI API Key Setup[/bold green]")
        else:
            print("\n🔑 OpenAI API Key Setup")

        try:
            current = self.config_manager.get_key("openai-api-key")
            if current:
                masked = self.config_manager._mask_value(current)
                print(f"📝 Current OpenAI API Key: {masked}")
                print("Enter a new key to update, or press Enter to keep current:")

            if RICH_AVAILABLE:
                try:
                    key = Prompt.ask("🔑 OpenAI API Key")
                    if key is None:
                        key = ""
                except KeyboardInterrupt:
                    key = ""
            else:
                key = input("🔑 OpenAI API Key: ").strip()

            if key:
                self.config_manager.set_key("openai-api-key", key)
                self._show_success("✅ OpenAI API key updated successfully!")
            elif current:
                self._show_message("✅ Kept existing OpenAI API key.")
            else:
                self._show_error("❌ No API key provided.")

        except KeyboardInterrupt:
            self._show_message("⚠️ Operation cancelled.")
        except Exception as e:
            self._show_error(f"❌ Error setting API key: {e}")

    def _handle_gemini_setup(self):
        """Handle Gemini API key setup with clear flow."""
        if RICH_AVAILABLE:
            console.print("\n[bold blue]💎 Gemini API Key Setup[/bold blue]")
        else:
            print("\n💎 Gemini API Key Setup")

        try:
            current = self.config_manager.get_key("gemini-api-key")
            if current:
                masked = self.config_manager._mask_value(current)
                print(f"📝 Current Gemini API Key: {masked}")
                print("Enter a new key to update, or press Enter to keep current:")

            if RICH_AVAILABLE:
                try:
                    key = Prompt.ask("💎 Gemini API Key")
                    if key is None:
                        key = ""
                except KeyboardInterrupt:
                    key = ""
            else:
                key = input("💎 Gemini API Key: ").strip()

            if key:
                self.config_manager.set_key("gemini-api-key", key)
                self._show_success("✅ Gemini API key updated successfully!")
            elif current:
                self._show_message("✅ Kept existing Gemini API key.")
            else:
                self._show_error("❌ No API key provided.")

        except KeyboardInterrupt:
            self._show_message("⚠️ Operation cancelled.")
        except Exception as e:
            self._show_error(f"❌ Error setting API key: {e}")

    def _handle_azure_setup(self):
        """Handle Azure configuration setup with clear flow."""
        if RICH_AVAILABLE:
            console.print(
                "\n[bold magenta]☁️ Azure OpenAI Configuration Setup[/bold magenta]")
        else:
            print("\n☁️ Azure OpenAI Configuration Setup")

        try:
            print("\n📋 Azure OpenAI requires four settings:")
            print("   • API Key")
            print("   • Endpoint URL")
            print("   • API Version")
            print("   • Deployment Name")

            current_key = self.config_manager.get_key("azure-api-key")
            current_endpoint = self.config_manager.get_key("azure-endpoint")
            current_version = self.config_manager.get_key("azure-api-version")
            current_deployment = self.config_manager.get_key(
                "azure-deployment")

            if current_key:
                print(
                    f"\n📝 Current API Key: {self.config_manager._mask_value(current_key)}")
            if current_endpoint:
                print(f"📝 Current Endpoint: {current_endpoint}")
            if current_version:
                print(f"📝 Current API Version: {current_version}")
            if current_deployment:
                print(f"📝 Current Deployment: {current_deployment}")

            print("\nEnter new values (press Enter to keep current):")

            if RICH_AVAILABLE:
                try:
                    api_key = Prompt.ask("🔑 Azure API Key")
                    if api_key is None or api_key == "":
                        api_key = current_key
                    endpoint = Prompt.ask(
                        "🌐 Azure Endpoint", default=current_endpoint)
                    if endpoint is None or endpoint == "":
                        endpoint = current_endpoint
                    api_version = Prompt.ask(
                        "🔢 API Version", default=current_version)
                    if api_version is None or api_version == "":
                        api_version = current_version
                    deployment = Prompt.ask(
                        "📦 Deployment Name", default=current_deployment)
                    if deployment is None or deployment == "":
                        deployment = current_deployment
                except KeyboardInterrupt:
                    api_key = current_key
                    endpoint = current_endpoint
                    api_version = current_version
                    deployment = current_deployment
            else:
                api_key = input("🔑 Azure API Key: ").strip() or current_key
                endpoint = input(
                    "🌐 Azure Endpoint: ").strip() or current_endpoint
                api_version = input(
                    "🔢 API Version: ").strip() or current_version
                deployment = input(
                    "📦 Deployment Name: ").strip() or current_deployment

            if api_key and endpoint and api_version and deployment:
                self.config_manager.set_key("azure-api-key", api_key)
                self.config_manager.set_key("azure-endpoint", endpoint)
                self.config_manager.set_key("azure-api-version", api_version)
                self.config_manager.set_key("azure-deployment", deployment)
                self._show_success(
                    "✅ Azure configuration updated successfully!")
            else:
                self._show_error(
                    "❌ All fields (API Key, Endpoint, API Version, Deployment) are required.")

        except KeyboardInterrupt:
            self._show_message("⚠️ Operation cancelled.")
        except Exception as e:
            self._show_error(f"❌ Error setting Azure configuration: {e}")

    def _handle_view_config(self):
        """Handle viewing current configuration."""
        keys = self.config_manager.list_keys()

        if RICH_AVAILABLE:
            if keys:
                config_text = Text()
                config_text.append(
                    "🔐 Configured API Keys:\n", style="bold green")

                for key, value in keys.items():
                    if "openai" in key.lower():
                        config_text.append(
                            f"  🔑 {key}: {value}\n", style="green")
                    elif "gemini" in key.lower():
                        config_text.append(
                            f"  💎 {key}: {value}\n", style="blue")
                    elif "azure" in key.lower():
                        config_text.append(
                            f"  ☁️  {key}: {value}\n", style="magenta")
                    else:
                        config_text.append(
                            f"  🔑 {key}: {value}\n", style="white")

                console.print(Panel(
                    config_text,
                    title="👁️ Current API Configuration",
                    border_style="cyan",
                    padding=(1, 2)
                ))
            else:
                empty_config = Text()
                empty_config.append(
                    "📭 No API keys configured yet.\n", style="yellow")
                empty_config.append(
                    "💡 Use options 1-3 to set up your API keys.", style="dim cyan")

                console.print(Panel(
                    empty_config,
                    title="👁️ Current API Configuration",
                    border_style="cyan",
                    padding=(1, 2)
                ))
        else:
            print("\n👁️ Current API Configuration")
            if keys:
                print("\n🔐 Configured API Keys:")
                for key, value in keys.items():
                    print(f"  {key}: {value}")
            else:
                print("\n📭 No API keys configured yet.")
                print("💡 Use options 1-3 to set up your API keys.")

    def _handle_delete_key(self):
        """Handle deleting a specific key."""
        if RICH_AVAILABLE:
            console.print("\n[bold red]🗑️ Delete API Key[/bold red]")
        else:
            print("\n🗑️ Delete API Key")

        keys = self.config_manager.list_keys()

        if not keys:
            self._show_error("❌ No keys to delete.")
            return

        print("\nAvailable keys to delete:")
        for i, key in enumerate(keys.keys(), 1):
            print(f"{i}. {key}")

        try:
            choice = input(
                "\nEnter key number to delete (or 'cancel'): ").strip()

            if choice.lower() in ['cancel', 'c']:
                self._show_message("✅ Operation cancelled.")
                return

            choice_num = int(choice)
            if 1 <= choice_num <= len(keys):
                key_to_delete = list(keys.keys())[choice_num - 1]
                if RICH_AVAILABLE:
                    confirm = Confirm.ask(
                        f"Are you sure you want to delete '{key_to_delete}'?", default=False)
                else:
                    confirm = input(
                        f"Are you sure you want to delete '{key_to_delete}'? (yes/no): ").strip().lower() in ['yes', 'y']

                if confirm:
                    self.config_manager.delete_key(key_to_delete)
                    self._show_success(f"✅ Deleted {key_to_delete}")
                else:
                    self._show_message("✅ Operation cancelled.")
            else:
                self._show_error("❌ Invalid choice.")

        except KeyboardInterrupt:
            self._show_message("⚠️ Operation cancelled.")
        except ValueError:
            self._show_error("❌ Please enter a valid number.")
        except Exception as e:
            self._show_error(f"❌ Error deleting key: {e}")

    def _handle_clear_all(self):
        """Handle clearing all configuration."""
        if RICH_AVAILABLE:
            console.print("\n[bold red]🧹 Clear All Configuration[/bold red]")
        else:
            print("\n🧹 Clear All Configuration")

        keys = self.config_manager.list_keys()

        if not keys:
            self._show_message("📭 No configuration to clear.")
            return

        print(f"\n⚠️ This will delete {len(keys)} API key(s):")
        for key in keys.keys():
            print(f"   • {key}")

        try:
            confirm = input(
                "\nAre you sure you want to clear ALL configuration? (type 'CLEAR ALL' to confirm): ").strip()

            if confirm == "CLEAR ALL":
                self.config_manager.clear_all()
                self._show_success("✅ All configuration cleared!")
            else:
                self._show_message("✅ Operation cancelled.")

        except KeyboardInterrupt:
            self._show_message("⚠️ Operation cancelled.")
        except Exception as e:
            self._show_error(f"❌ Error clearing configuration: {e}")

    def _ask_next_action(self):
        """Ask user what to do next after an action."""
        if RICH_AVAILABLE:
            next_action_panel = Text()
            next_action_panel.append(
                "What would you like to do next?\n\n", style="bold white")
            next_action_panel.append(
                "1. 🔄 Return to API Configuration Menu\n", style="cyan")
            next_action_panel.append("2. 🔙 Back to Main Menu", style="yellow")

            console.print(Panel(
                next_action_panel,
                title="🎯 Next Action",
                border_style="blue",
                padding=(1, 2)
            ))

            choice = Prompt.ask("Choose", choices=["1", "2"], default="1")
        else:
            print("\n" + "="*50)
            print("What would you like to do next?")
            print("1. Return to API Configuration Menu")
            print("2. Back to Main Menu")
            print("="*50)
            choice = input("Choose (1-2) [1]: ").strip() or "1"

        try:
            if choice == "1":
                return
            elif choice == "2":
                self._show_message("🔙 Returning to main menu...")
                raise KeyboardInterrupt
            else:
                self._show_error("Invalid choice, returning to menu...")
        except KeyboardInterrupt:
            raise

    def _get_choice(self) -> int:
        """Get user choice from menu."""
        while True:
            try:
                if RICH_AVAILABLE:
                    choice = Prompt.ask("Select option (1-7)", default="7")
                else:
                    choice = input("Select option (1-7) [7]: ").strip() or "7"

                choice_num = int(choice)
                if 1 <= choice_num <= 7:
                    return choice_num
                else:
                    self._show_error("Please enter a number between 1 and 7.")
            except KeyboardInterrupt:
                raise
            except ValueError:
                self._show_error("Please enter a valid number.")

    def _show_success(self, message: str):
        """Set Gemini API key."""
        try:
            current = self.config_manager.get_key("gemini-api-key")
            if current:
                masked = self.config_manager._mask_value(current)
                print(f"Current Gemini API Key: {masked}")

            print("Enter Gemini API Key (press Enter when done):")
            if RICH_AVAILABLE:
                key = input().strip()
            else:
                key = input().strip()

            if key:
                self.config_manager.set_key("gemini-api-key", key)
                self._show_success("Gemini API key saved securely!")
            else:
                self._show_error("No key entered.")
        except KeyboardInterrupt:
            self._show_message("Operation cancelled.")
        except Exception as e:
            self._show_error(f"Error setting API key: {e}")

    def _set_azure_config(self):
        """Set Azure OpenAI configuration."""
        try:
            print("\nAzure OpenAI Configuration")

            current_key = self.config_manager.get_key("azure-api-key")
            current_endpoint = self.config_manager.get_key("azure-endpoint")
            current_deployment = self.config_manager.get_key(
                "azure-deployment")

            if current_key:
                print(
                    f"Current API Key: {self.config_manager._mask_value(current_key)}")
            if current_endpoint:
                print(f"Current Endpoint: {current_endpoint}")
            if current_deployment:
                print(f"Current Deployment: {current_deployment}")

            print("Enter Azure OpenAI API Key (press Enter when done):")
            api_key = input().strip()

            print("Enter Azure Endpoint (e.g., https://your-resource.openai.azure.com/):")
            endpoint = input().strip()

            print("Enter Deployment Name (e.g., gpt-4):")
            deployment = input().strip()

            if api_key and endpoint and deployment:
                self.config_manager.set_key("azure-api-key", api_key)
                self.config_manager.set_key("azure-endpoint", endpoint)
                self.config_manager.set_key("azure-deployment", deployment)
                self.config_manager.set_key(
                    "azure-api-version", "2024-12-01-preview")
                self._show_success("Azure configuration saved securely!")
            else:
                self._show_error(
                    "All fields (API Key, Endpoint, Deployment) are required.")
        except KeyboardInterrupt:
            self._show_message("Operation cancelled.")
        except Exception as e:
            self._show_error(f"Error setting Azure configuration: {e}")

    def _view_configuration(self):
        """View current configuration."""
        keys = self.config_manager.list_keys()

        if RICH_AVAILABLE:
            if keys:
                console.print(
                    "\n[bold green]Current Configuration:[/bold green]")
                for key, value in keys.items():
                    print(f"  {key}: {value}")
            else:
                console.print("[yellow]No configuration set.[/yellow]")
        else:
            print("\nCurrent Configuration:")
            if keys:
                for key, value in keys.items():
                    print(f"  {key}: {value}")
            else:
                print("No configuration set.")

    def _delete_key(self):
        """Delete a specific key."""
        keys = self.config_manager.list_keys()

        if not keys:
            self._show_error("No configuration to delete.")
            return

        if RICH_AVAILABLE:
            console.print(
                "\n[bold yellow]Available keys to delete:[/bold yellow]")
            for i, key in enumerate(keys.keys(), 1):
                print(f"{i}. {key}")

            try:
                choice = Prompt.ask(
                    "Enter key number to delete (or 'cancel')", default="cancel")
                if choice.lower() == "cancel":
                    return

                choice_num = int(choice)
                if 1 <= choice_num <= len(keys):
                    key_to_delete = list(keys.keys())[choice_num - 1]
                    self.config_manager.delete_key(key_to_delete)
                    self._show_success(f"Deleted {key_to_delete}")
                else:
                    self._show_error("Invalid choice.")
            except ValueError:
                self._show_error("Invalid input.")
        else:
            print("\nAvailable keys to delete:")
            for i, key in enumerate(keys.keys(), 1):
                print(f"{i}. {key}")

            choice = input(
                "Enter key number to delete (or empty to cancel): ").strip()
            if not choice:
                return

            try:
                choice_num = int(choice)
                if 1 <= choice_num <= len(keys):
                    key_to_delete = list(keys.keys())[choice_num - 1]
                    self.config_manager.delete_key(key_to_delete)
                    self._show_success(f"Deleted {key_to_delete}")
                else:
                    self._show_error("Invalid choice.")
            except ValueError:
                self._show_error("Invalid input.")

    def _clear_all_config(self):
        """Clear all configuration."""
        if RICH_AVAILABLE:
            confirm = Confirm.ask(
                "Are you sure you want to clear ALL configuration?", default=False)
        else:
            response = input(
                "Are you sure you want to clear ALL configuration? (yes/no): ").strip().lower()
            confirm = response in ['yes', 'y']

        if confirm:
            self.config_manager.clear_all()
            self._show_success("All configuration cleared!")
        else:
            self._show_message("Operation cancelled.")

    def _show_success(self, message: str):
        """Show success message."""
        if RICH_AVAILABLE:
            console.print(f"[green]✅ {message}[/green]")
        else:
            print(f"✅ {message}")

    def _show_error(self, message: str):
        """Show error message."""
        if RICH_AVAILABLE:
            console.print(f"[red]❌ {message}[/red]")
        else:
            print(f"❌ {message}")

    def _show_message(self, message: str):
        """Show regular message."""
        if RICH_AVAILABLE:
            console.print(f"[blue]{message}[/blue]")
        else:
            print(message)

    def _pause(self):
        """Pause for user to read messages."""
        try:
            if RICH_AVAILABLE:
                Prompt.ask("\nPress Enter to continue",
                           default="", show_default=False)
            else:
                input("\nPress Enter to continue...")
        except KeyboardInterrupt:
            pass
