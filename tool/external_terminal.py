import os
import sys
import json
import shutil
import time
import uuid
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, Any

from util.logging import get_logger, log_error


logger = get_logger("external_terminal")


class ExternalTerminalSession:
    def __init__(self, working_dir: Path, env: Dict[str, Any]):
        self.working_dir = working_dir
        self.env = env
        self.session_dir = Path(tempfile.gettempdir()) / \
            f"lyne_terminal_{uuid.uuid4().hex}"
        self.command_file = self.session_dir / "command.txt"
        self.run_file = self.session_dir / "run.flag"
        self.cancel_file = self.session_dir / "cancel.flag"
        self.result_file = self.session_dir / "result.json"
        self.process: subprocess.Popen | None = None
        self.available = False

    def launch(self, initial_command: str) -> bool:
        try:
            self.session_dir.mkdir(parents=True, exist_ok=True)
            self.command_file.write_text(initial_command, encoding="utf-8")
        except Exception as exc:
            log_error(exc, "Failed to prepare external terminal session", logger)
            return False
        launcher = self._build_launcher()
        if not launcher:
            return False
        try:
            self.process = subprocess.Popen(launcher["argv"], cwd=str(
                self.working_dir), env=self.env, **launcher.get("popen_kwargs", {}))
            self.available = True
            import time
            time.sleep(1)
            if self.process.poll() is not None:
                log_error(Exception("Process exited immediately"),
                          "External terminal process died", logger)
                return False
            return True
        except Exception as exc:
            log_error(exc, "Failed to start external terminal", logger)
            return False

    def _build_launcher(self) -> Dict[str, Any] | None:
        runner_script = Path(__file__).parent / "external_terminal_runner.py"
        if not runner_script.exists():
            return None
        runner_cmd = [sys.executable, str(
            runner_script), "--session", str(self.session_dir), "--path", str(self.working_dir)]
        if os.name == "nt":
            creation_flag = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
            if not creation_flag:
                return None
            return {"argv": runner_cmd, "popen_kwargs": {"creationflags": creation_flag}}
        if sys.platform == "darwin":
            script = f"cd {self.working_dir} && {sys.executable} '{runner_script}' --session '{self.session_dir}' --path '{self.working_dir}'"
            return {"argv": ["osascript", "-e", f'tell application "Terminal" to do script "{script}"'], "popen_kwargs": {}}
        term_candidates = ["x-terminal-emulator",
                           "gnome-terminal", "konsole", "xfce4-terminal", "xterm"]
        for candidate in term_candidates:
            if shutil.which(candidate):
                return {"argv": [candidate, "-e", sys.executable, str(runner_script), "--session", str(self.session_dir), "--path", str(self.working_dir)], "popen_kwargs": {}}
        return None

    def update_command(self, command: str) -> None:
        if not self.available:
            return
        try:
            self.command_file.write_text(command, encoding="utf-8")
        except Exception as exc:
            log_error(exc, "Failed to update external terminal command", logger)

    def cancel(self) -> None:
        if not self.available:
            return
        try:
            self.cancel_file.write_text("cancel", encoding="utf-8")
        except Exception:
            pass

    def start(self) -> None:
        if not self.available:
            return
        try:
            self.run_file.write_text("run", encoding="utf-8")
        except Exception as exc:
            log_error(exc, "Failed to signal external terminal start", logger)

    def wait_for_completion(self) -> Dict[str, Any] | None:
        if not self.available:
            return None
        while True:
            if self.result_file.exists():
                try:
                    return json.loads(self.result_file.read_text(encoding="utf-8"))
                except Exception:
                    return {"status": "unknown"}
            if self.process and self.process.poll() is not None:
                if self.result_file.exists():
                    try:
                        return json.loads(self.result_file.read_text(encoding="utf-8"))
                    except Exception:
                        return {"status": "unknown"}
                return {"status": "closed"}
            time.sleep(0.5)

    def cleanup(self) -> None:
        if not self.session_dir.exists():
            return
        try:
            for item in self.session_dir.iterdir():
                try:
                    item.unlink()
                except Exception:
                    pass
            self.session_dir.rmdir()
        except Exception:
            pass
        self.available = False
