#!/usr/bin/env python3
import os
import sys
import shlex
import subprocess
from pathlib import Path

from util.logging import get_logger, log_function_call, log_error, log_warning


logger = get_logger("terminal")


try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    RICH_AVAILABLE = True
    console = Console()
except ImportError:
    RICH_AVAILABLE = False
    console = None


def _resolve_project_root() -> Path:
    try:
        root = os.environ.get('LYNE_OPERATING_PATH')
        if root:
            return Path(root).resolve()
    except Exception:
        pass
    return Path(os.getcwd()).resolve()


def _is_within_path(target: Path, root: Path) -> bool:
    try:
        return str(target.resolve()).startswith(str(root.resolve()))
    except Exception:
        return False


def _parse_command(command) -> list:
    if isinstance(command, list):
        return [str(x) for x in command if str(x).strip()]
    if not isinstance(command, str):
        raise ValueError("command must be a string or list")
    cmd = command.strip()
    if not cmd:
        raise ValueError("command cannot be empty")
    if os.name == 'nt':
        return shlex.split(cmd, posix=False)
    return shlex.split(cmd)


def _build_command_str(command) -> str:
    if isinstance(command, str):
        return command
    if isinstance(command, list):
        if os.name == 'nt':
            return " ".join([str(x) for x in command])
        return " ".join([shlex.quote(str(x)) for x in command])
    raise ValueError("command must be a string or list")


def _detect_python_venv(start_dir: Path, project_root: Path) -> Path | None:
    try:
        candidates = [".venv", "venv", "env"]
        current = start_dir.resolve()
        root = project_root.resolve()
        while True:
            for name in candidates:
                candidate = current / name
                if (candidate / ("Scripts" if os.name == 'nt' else "bin") / ("python.exe" if os.name == 'nt' else "python")).exists():
                    return candidate
            if current == root:
                break
            parent = current.parent
            if parent == current:
                break
            current = parent
    except Exception:
        return None
    return None


def _detect_node_bins(start_dir: Path, project_root: Path) -> Path | None:
    try:
        current = start_dir.resolve()
        root = project_root.resolve()
        while True:
            candidate = current / "node_modules" / ".bin"
            if candidate.exists():
                return candidate
            if current == root:
                break
            parent = current.parent
            if parent == current:
                break
            current = parent
    except Exception:
        return None
    return None


def _looks_like_absolute_path(token: str) -> bool:
    try:
        p = Path(token)
        return p.is_absolute()
    except Exception:
        return False


def _is_dangerous_command(argv: list) -> bool:
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


def _wrap_output(output: str) -> str:
	start = "=== TERMINAL OUTPUT START ==="
	end = "=== TERMINAL OUTPUT END ==="
	if output is None:
		output = ""
	needs_nl = "" if output.endswith("\n") else "\n"
	return f"{start}\n{output}{needs_nl}{end}"


def _show_confirmation(command_str: str, working_dir: Path, auto_activate: bool, venv_dir: Path | None, node_bins: Path | None) -> bool:
    try:
        cmd_text = command_str
        wd = str(working_dir)
        if RICH_AVAILABLE and console:
            content = Text()
            content.append(f"Command: {cmd_text}\n", style="white")
            content.append(f"Path: {wd}\n", style="cyan")
            console.print(Panel(content, title="Run Terminal Command",
                          border_style="green", padding=(1, 1)))
            console.print("Proceed? ", style="bold yellow", end="")
            console.print("(y/n): ", style="dim", end="")
            resp = input().strip().lower()
        else:
            print("\n==============================")
            print("Run Terminal Command")
            print(f"Command: {cmd_text}")
            print(f"Path: {wd}")
            print("==============================")
            resp = input("Proceed? (y/n): ").strip().lower()
        return resp in {"y", "yes"}
    except Exception:
        return False


def run_terminal_command(command, path: str, auto_activate: bool = True, timeout_sec: int = 60) -> str:
    try:
        log_function_call("run_terminal_command", {
                          "path": path, "auto_activate": auto_activate, "timeout_sec": timeout_sec}, logger)
        project_root = _resolve_project_root()
        if not path:
            raise ValueError("path is required")
        working_dir = Path(path).resolve()
        if not _is_within_path(working_dir, project_root):
            error = f"Tried to run this command {command} on this path {path} but it encounter this error path_outside_project"
            return error
        if not working_dir.exists() or not working_dir.is_dir():
            error = f"Tried to run this command {command} on this path {path} but it encounter this error invalid_path"
            return error
        argv = _parse_command(command)
        command_str = _build_command_str(command)
        if not argv and not command_str:
            error = f"Tried to run this command {command} on this path {path} but it encounter this error empty_command"
            return error
        if _is_dangerous_command(argv):
            error = f"Tried to run this command {command} on this path {path} but it encounter this error blocked_dangerous_command"
            return error
        for tok in argv:
            if _looks_like_absolute_path(tok):
                pt = Path(tok)
                if not _is_within_path(pt, project_root):
                    error = f"Tried to run this command {command} on this path {path} but it encounter this error absolute_path_outside_project"
                    return error
        venv_dir = None
        node_bins = None
        env = os.environ.copy()
        if auto_activate:
            venv_dir = _detect_python_venv(working_dir, project_root)
            node_bins = _detect_node_bins(working_dir, project_root)
            path_parts = []
            if venv_dir:
                bin_dir = venv_dir / ("Scripts" if os.name == 'nt' else "bin")
                path_parts.append(str(bin_dir))
            if node_bins:
                path_parts.append(str(node_bins))
            if path_parts:
                env["PATH"] = os.pathsep.join(
                    path_parts + [env.get("PATH", "")])
            if venv_dir:
                env["VIRTUAL_ENV"] = str(venv_dir)
        if not _show_confirmation(command_str, working_dir, auto_activate, venv_dir, node_bins):
            return f"Tried to run this command {command} on this path {path} but it encounter this error cancelled_by_user"
        try:
            if not isinstance(timeout_sec, int):
                timeout_sec = int(timeout_sec)
        except Exception:
            timeout_sec = 60
        if timeout_sec < 5:
            timeout_sec = 5
        if timeout_sec > 90:
            timeout_sec = 90

        encoding = sys.getdefaultencoding()
        try:
            if os.name == 'nt':
                shell_argv = ["cmd.exe", "/d", "/s", "/c", command_str]
            else:
                bash = Path("/bin/bash")
                if bash.exists():
                    shell_argv = [str(bash), "-lc", f"set -o pipefail; {command_str}"]
                else:
                    shell_argv = ["/bin/sh", "-lc", command_str]
            proc = subprocess.Popen(
                shell_argv,
                cwd=str(working_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env=env,
                shell=False,
                text=True,
                encoding=encoding,
                errors='replace'
            )
            try:
                stdout, _ = proc.communicate(timeout=timeout_sec)
            except subprocess.TimeoutExpired:
                proc.kill()
                try:
                    stdout, _ = proc.communicate(timeout=5)
                except Exception:
                    stdout = ""
                return f"Tried to run this command {command} on this path {path} but it encounter this error timeout_{timeout_sec}s"
            exit_code = proc.returncode
            output = stdout if stdout is not None else ""
            if exit_code == 0:
                return _wrap_output(output)
            return f"Tried to run this command {command} on this path {path} but it encounter this error exit_code_{exit_code}"
        except FileNotFoundError:
            return f"Tried to run this command {command} on this path {path} but it encounter this error executable_not_found"
        except Exception as e:
            log_error(e, "Terminal command execution failed", logger)
            return f"Tried to run this command {command} on this path {path} but it encounter this error {str(e)}"
    except Exception as e:
      log_error(e, "run_terminal_command unexpected failure", logger)
    return f"Tried to run this command {command} on this path {path} but it encounter this error {str(e)}"