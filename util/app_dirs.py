"""
Application directory management for Lynecode.

Handles proper directory placement based on installation method:
- Development: Use local directories (log/, output/)
- Pip installation: Use system directories (AppData, .config, etc.)
"""

import os
import sys
from pathlib import Path
from typing import Tuple


def _is_pip_installation() -> bool:
    """
    Detect if Lynecode is running from pip installation or development.

    Returns:
        True if installed via pip, False if running from development
    """
    try:
        main_module = sys.modules.get('__main__')
        if not main_module or not hasattr(main_module, '__file__'):
            return True

        main_file = Path(main_module.__file__).resolve()

        site_packages_indicators = [
            'site-packages', 'dist-packages', 'Python', 'lib']
        main_file_str = str(main_file)

        for indicator in site_packages_indicators:
            if indicator in main_file_str:
                return True

        package_root = main_file.parent
        while package_root != package_root.parent:
            if (package_root / 'pyproject.toml').exists() or (package_root / 'setup.py').exists():
                return False
            package_root = package_root.parent

        return True

    except Exception:
        return True


def get_app_directories() -> Tuple[Path, Path]:
    r"""
    Get appropriate directories for logs and conversation history.

    Returns:
        Tuple of (log_dir, conversation_history_dir)

    Behavior:
        - Development: Returns ('log', 'output/conversation_history') in current directory
        - Pip installation: Returns system directories
          - Windows: %LOCALAPPDATA%\lynecode\logs, %APPDATA%\lynecode\conversations
          - Unix: ~/.cache/lynecode/logs, ~/.local/share/lynecode/conversations
    """
    if not _is_pip_installation():
        log_dir = Path("log")
        conv_dir = Path("output") / "conversation_history"
        return log_dir, conv_dir

    if os.name == 'nt':
        local_app_data = os.environ.get('LOCALAPPDATA')
        app_data = os.environ.get('APPDATA')

        if not local_app_data:
            local_app_data = os.path.expanduser('~\\AppData\\Local')
        if not app_data:
            app_data = os.path.expanduser('~\\AppData\\Roaming')

        log_dir = Path(local_app_data) / 'lynecode' / 'logs'
        conv_dir = Path(app_data) / 'lynecode' / 'conversations'
    else:
        home = Path.home()
        log_dir = home / '.cache' / 'lynecode' / 'logs'
        conv_dir = home / '.local' / 'share' / 'lynecode' / 'conversations'

    return log_dir, conv_dir


def get_log_directory() -> Path:
    """Get the appropriate log directory."""
    log_dir, _ = get_app_directories()
    return log_dir


def get_conversation_history_directory() -> Path:
    """Get the appropriate conversation history directory."""
    _, conv_dir = get_app_directories()
    return conv_dir


def ensure_app_directories() -> None:
    """Ensure all application directories exist."""
    log_dir, conv_dir = get_app_directories()
    log_dir.mkdir(parents=True, exist_ok=True)
    conv_dir.mkdir(parents=True, exist_ok=True)
