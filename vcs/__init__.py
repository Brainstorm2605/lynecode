"""
Version Control System for Lyne

Simple VCS focused on recovering from AI mistakes.
Provides rolling backups (last 10 edits) and menu-based reversion.
"""

from .backup_manager import BackupManager
from .diff_viewer import DiffViewer
from .version_control import VersionControl

__all__ = ['BackupManager', 'DiffViewer', 'VersionControl']
