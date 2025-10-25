#!/usr/bin/env python3
import os
import sys
import subprocess
import threading
from pathlib import Path
from typing import Dict, Any, Optional

from util.logging import get_logger, log_function_call, log_error
from .external_terminal import ExternalTerminalSession
from .terminal_guard import (
    parse_command,
    build_command_str,
    check_command_constraints,
)


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


def _wrap_output(output: str) -> str:
    start = "=== TERMINAL OUTPUT START ==="
    end = "=== TERMINAL OUTPUT END ==="
    if output is None:
        output = ""
    needs_nl = "" if output.endswith("\n") else "\n"
    return f"{start}\n{output}{needs_nl}{end}"


def _show_session_window(command_str: str, working_dir: Path, venv_dir: Path | None, node_bins: Path | None) -> None:
    info_lines = []
    info_lines.append(("Command", command_str))
    info_lines.append(("Path", str(working_dir)))
    if venv_dir:
        info_lines.append(("Python venv", str(venv_dir)))
    if node_bins:
        info_lines.append(("Node bins", str(node_bins)))
    if RICH_AVAILABLE and console:
        content = Text()
        for label, value in info_lines:
            content.append(f"{label}: ", style="bold white")
            content.append(f"{value}\n", style="cyan")
        console.print(Panel(content, title="Terminal Session",
                      border_style="cyan", padding=(1, 1)))
    else:
        print("\n==============================")
        print("Terminal Session")
        for label, value in info_lines:
            print(f"{label}: {value}")
        print("==============================")


def _prompt_session_choice() -> str:
    if RICH_AVAILABLE and console:
        console.print(
            Text("Options: [Enter] run • e edit • n cancel", style="bold yellow"))
        resp = console.input(
            Text("Choice: ", style="bold cyan")).strip().lower()
    else:
        print("Options: [Enter] run, e edit, n cancel")
        resp = input("Choice: ").strip().lower()
    if resp in {"", "r", "run", "y", "yes"}:
        return "run"
    if resp in {"e", "edit"}:
        return "edit"
    if resp in {"n", "no", "cancel"}:
        return "cancel"
    return "unknown"


def _render_message(text: str, style: str = "white") -> None:
    if RICH_AVAILABLE and console:
        console.print(Text(text, style=style))
    else:
        print(text)


def _prompt_command_edit(current: str) -> str | None:
    if RICH_AVAILABLE and console:
        new_cmd = console.input(Text(
            "Enter new command (blank keeps current, 'abort' cancels edit): ", style="bold cyan"))
    else:
        new_cmd = input(
            "Enter new command (blank keeps current, 'abort' cancels edit): ")
    new_cmd = new_cmd.strip()
    if not new_cmd:
        return current
    if new_cmd.lower() == "abort":
        return None
    return new_cmd


def _render_output_line(line: str) -> None:
    if RICH_AVAILABLE and console:
        console.print(line, end="")
    else:
        sys.stdout.write(line)
        sys.stdout.flush()


def _stream_process_output(proc: subprocess.Popen, collector: list[str], stop_event: threading.Event) -> None:
    try:
        if not proc.stdout:
            return
        for line in iter(proc.stdout.readline, ""):
            if stop_event.is_set():
                break
            collector.append(line)
            _render_output_line(line)
    finally:
        try:
            if proc.stdout:
                proc.stdout.close()
        except Exception:
            pass


def _build_shell_argv(command_str: str) -> list[str]:
    if os.name == 'nt':
        return ["cmd.exe", "/d", "/s", "/c", command_str]
    bash = Path("/bin/bash")
    if bash.exists():
        return [str(bash), "-lc", f"set -o pipefail; {command_str}"]
    return ["/bin/sh", "-lc", command_str]


class InteractiveTerminalSession:
    def __init__(self, command_str: str, argv: list[str], working_dir: Path, env: Dict[str, Any], project_root: Path, timeout_sec: int, venv_dir: Path | None, node_bins: Path | None, external_session: Optional[ExternalTerminalSession] = None):
        self.command_str = command_str
        self.argv = argv
        self.working_dir = working_dir
        self.env = env
        self.project_root = project_root
        self.timeout_sec = timeout_sec
        self.venv_dir = venv_dir
        self.node_bins = node_bins
        self.external_session = external_session
        self.external_started = False

    def start(self) -> dict:
        while True:
            _show_session_window(
                self.command_str, self.working_dir, self.venv_dir, self.node_bins)
            choice = _prompt_session_choice()
            if choice == "unknown":
                _render_message("Invalid choice.", "yellow")
                continue
            if choice == "cancel":
                _render_message("Session cancelled.", "yellow")
                if self.external_session and self.external_started:
                    self.external_session.cancel()
                    self.external_session.cleanup()
                return {"status": "cancelled"}
            if choice == "edit":
                self._edit_command()
                continue
            if choice == "run":
                return self._run_command()

    def _edit_command(self) -> None:
        new_cmd = _prompt_command_edit(self.command_str)
        if new_cmd is None:
            _render_message("Edit cancelled.", "yellow")
            return
        if new_cmd == self.command_str:
            return
        try:
            new_argv = parse_command(new_cmd)
        except Exception as e:
            _render_message(f"Invalid command: {str(e)}", "red")
            return
        constraint = check_command_constraints(new_argv, self.project_root)
        if constraint:
            _render_message(f"Command rejected: {constraint}", "red")
            return
        self.command_str = build_command_str(new_argv)
        self.argv = new_argv
        if self.external_session and self.external_started:
            self.external_session.update_command(self.command_str)
        _render_message("Command updated.", "green")

    def _run_command(self) -> dict:
        if self.external_session:
            return self._run_external()
        _render_message(
            "Starting terminal session. Press Ctrl+C to stop.", "cyan")
        encoding = sys.getdefaultencoding()
        shell_argv = _build_shell_argv(self.command_str)
        output_lines: list[str] = []
        stop_event = threading.Event()
        proc = None
        try:
            proc = subprocess.Popen(
                shell_argv,
                cwd=str(self.working_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env=self.env,
                shell=False,
                text=True,
                encoding=encoding,
                errors='replace',
                bufsize=1
            )
        except FileNotFoundError:
            return {"status": "error", "error": "executable_not_found"}
        except Exception as e:
            return {"status": "error", "error": str(e)}
        reader = threading.Thread(target=_stream_process_output, args=(
            proc, output_lines, stop_event), daemon=True)
        reader.start()
        try:
            proc.wait(timeout=self.timeout_sec)
        except subprocess.TimeoutExpired:
            stop_event.set()
            proc.kill()
            reader.join(timeout=1)
            return {"status": "timeout"}
        except KeyboardInterrupt:
            stop_event.set()
            proc.kill()
            reader.join(timeout=1)
            return {"status": "interrupted"}
        reader.join(timeout=1)
        if reader.is_alive():
            stop_event.set()
            reader.join(timeout=1)
        exit_code = proc.returncode
        output = ''.join(output_lines)
        if exit_code == 0:
            _render_message("Process exited with code 0.", "green")
        else:
            _render_message(f"Process exited with code {exit_code}.", "red")
        return {"status": "completed", "exit_code": exit_code, "output": output}

    def _run_external(self) -> dict:
        if not self.external_session:
            return {"status": "error", "error": "external_unavailable"}
        if not self.external_started:
            if not self.external_session.launch(self.command_str):
                return {"status": "error", "error": "external_launch_failed"}
            self.external_started = True
        self.external_session.update_command(self.command_str)
        self.external_session.start()
        result = self.external_session.wait_for_completion()
        self.external_session.cleanup()
        if not result:
            return {"status": "error", "error": "external_terminal_closed"}
        status = result.get("status")
        if status == "completed":
            exit_code = result.get("exit_code", 0)
            message = result.get(
                "message", "Command executed in external terminal.")
            return {"status": "completed", "exit_code": exit_code, "output": message}
        if status == "cancelled":
            return {"status": "cancelled"}
        if status == "interrupted":
            return {"status": "interrupted"}
        if status == "error":
            return {"status": "error", "error": result.get("error", "external_error")}
        return {"status": "error", "error": "external_terminal_closed"}


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
        argv = parse_command(command)
        command_str = build_command_str(command)
        constraint_error = check_command_constraints(argv, project_root)
        if constraint_error:
            return f"Tried to run this command {command} on this path {path} but it encounter this error {constraint_error}"
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
        if not isinstance(timeout_sec, int):
            try:
                timeout_sec = int(timeout_sec)
            except Exception:
                timeout_sec = 60
        timeout_sec = max(5, min(timeout_sec, 160))

        external_session = ExternalTerminalSession(working_dir, env)
        session = InteractiveTerminalSession(
            command_str, argv, working_dir, env, project_root, timeout_sec, venv_dir, node_bins, external_session)
        result = session.start()
        status = result.get("status")
        if status == "cancelled":
            return f"Tried to run this command {command} on this path {path} but it encounter this error cancelled_by_user"
        if status == "timeout":
            return f"Tried to run this command {command} on this path {path} but it encounter this error timeout_{timeout_sec}s"
        if status == "interrupted":
            return f"Tried to run this command {command} on this path {path} but it encounter this error interrupted_by_user"
        if status == "error":
            return f"Tried to run this command {command} on this path {path} but it encounter this error {result.get('error', 'unknown_error')}"
        if status == "completed":
            exit_code = result.get("exit_code", 0)
            output = result.get("output", "")
            if exit_code == 0:
                return _wrap_output(output)
            return f"Tried to run this command {command} on this path {path} but it encounter this error exit_code_{exit_code}"
        return f"Tried to run this command {command} on this path {path} but it encounter this error unexpected_session_state"
    except Exception as e:
        log_error(e, "run_terminal_command unexpected failure", logger)
    return f"Tried to run this command {command} on this path {path} but it encounter this error {str(e)}"
