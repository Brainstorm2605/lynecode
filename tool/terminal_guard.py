import os
import shlex
from pathlib import Path
from typing import List, Union


def parse_command(command: Union[str, List[str]]) -> List[str]:
    if isinstance(command, list):
        return [str(x) for x in command if str(x).strip()]
    if not isinstance(command, str):
        raise ValueError("command must be a string or list")
    cmd = command.strip()
    if not cmd:
        raise ValueError("command cannot be empty")
    if os.name == "nt":
        return shlex.split(cmd, posix=False)
    return shlex.split(cmd)


def build_command_str(command: Union[str, List[str]]) -> str:
    if isinstance(command, str):
        return command
    if isinstance(command, list):
        if os.name == "nt":
            return " ".join([str(x) for x in command])
        return " ".join([shlex.quote(str(x)) for x in command])
    raise ValueError("command must be a string or list")


def _looks_like_absolute_path(token: str) -> bool:
    try:
        return Path(token).is_absolute()
    except Exception:
        return False


def _is_dangerous_command(argv: List[str]) -> bool:
    argv_lower = [str(x).lower() for x in argv]
    joined = " ".join(argv_lower)
    if "rm -rf /" in joined or "rm -fr /" in joined:
        return True
    if argv_lower and argv_lower[0] in {"diskpart", "format", "shutdown", "reboot", "mkfs", "mkfs.ext4", "mkfs.ntfs"}:
        return True
    if argv_lower and argv_lower[0] in {"reg"} and any(x == "delete" for x in argv_lower[1:3]):
        return True
    if argv_lower and argv_lower[0] in {"rmdir", "rd"} and any(x in {"/s", "/q"} for x in argv_lower[1:]):
        return True
    if "remove-item" in argv_lower and "-recurse" in argv_lower and "-force" in argv_lower:
        return True
    if argv_lower and argv_lower[0] == "sudo":
        return True
    if "chown -r /" in joined or "chmod -r 777 /" in joined:
        return True
    return False


def check_command_constraints(argv: List[str], project_root: Path) -> str | None:
    if not argv:
        return "empty_command"
    if _is_dangerous_command(argv):
        return "blocked_dangerous_command"
    for tok in argv:
        if _looks_like_absolute_path(tok):
            pt = Path(tok)
            try:
                if not str(pt.resolve()).startswith(str(project_root.resolve())):
                    return "absolute_path_outside_project"
            except Exception:
                return "absolute_path_outside_project"
    return None
