from util.logging import get_logger, log_error
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

lynecode_root = Path(__file__).parent.parent
if str(lynecode_root) not in sys.path:
    sys.path.insert(0, str(lynecode_root))


logger = get_logger("external_terminal_runner")


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except Exception:
        return ""


def write_json(path: Path, data) -> None:
    try:
        path.write_text(json.dumps(data), encoding="utf-8")
    except Exception as exc:
        log_error(exc, "Failed to write external terminal result", logger)


def read_exit_code(path: Path) -> int:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("exit_code", 0)
    except Exception:
        return 0


def main() -> None:
    try:
        _main_impl()
    except Exception as exc:
        print(f"\n[ERROR] Fatal error in terminal runner: {exc}")
        import traceback
        traceback.print_exc()
        input("\nPress Enter to close...")


def _main_impl() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--session", required=True)
    parser.add_argument("--path", required=True)
    args = parser.parse_args()

    session_dir = Path(args.session)
    working_dir = Path(args.path)

    command_file = session_dir / "command.txt"
    run_file = session_dir / "run.flag"
    cancel_file = session_dir / "cancel.flag"
    result_file = session_dir / "result.json"

    for directory in [session_dir, working_dir]:
        if not directory.exists():
            write_json(result_file, {"status": "error",
                       "error": f"missing_dir:{directory}"})
            input(
                f"\n[ERROR] Directory does not exist: {directory}\nPress Enter to close...")
            return

    print("=" * 70)
    print("LYNE TERMINAL")
    print("=" * 70)
    print(f"Directory: {working_dir}")

    current_command = read_text(command_file)
    if current_command:
        print(f"Command: {current_command}")
    else:
        print("Waiting for command...")

    print("=" * 70)
    print("")

    while True:
        if cancel_file.exists():
            print("\n[CANCELLED] Session cancelled by agent.")
            write_json(result_file, {"status": "cancelled"})
            input("\nPress Enter to close...")
            return

        latest_file_command = read_text(command_file)
        if latest_file_command and latest_file_command != current_command:
            current_command = latest_file_command
            print(f"\n[UPDATED] Command updated to: {current_command}")

        if run_file.exists():
            try:
                run_file.unlink()
            except Exception:
                pass
            print("")
            status = execute_command(current_command, working_dir, result_file)
            if status == "completed":
                print(f"\n[EXIT CODE: {read_exit_code(result_file)}]")
            else:
                print(f"\n[STATUS: {status.upper()}]")
            input("\nPress Enter to close...")
            return

        time.sleep(0.2)


def execute_command(command: str, working_dir: Path, result_file: Path) -> str:
    if not command:
        write_json(result_file, {"status": "error", "error": "empty_command"})
        return "error"

    if os.name == "nt":
        shell_argv = ["cmd.exe", "/d", "/s", "/c", command]
    else:
        shell = os.environ.get("SHELL") or "/bin/bash"
        shell_argv = [shell, "-lc", command]

    try:
        proc = subprocess.Popen(
            shell_argv,
            cwd=str(working_dir),
            stdin=None,
            stdout=None,
            stderr=None
        )
        proc.wait()
        write_json(result_file, {"status": "completed",
                   "exit_code": proc.returncode})
        return "completed"
    except KeyboardInterrupt:
        print("\n[INTERRUPTED]")
        write_json(result_file, {"status": "interrupted"})
        return "interrupted"
    except Exception as exc:
        log_error(exc, "External execution failed", logger)
        write_json(result_file, {"status": "error", "error": str(exc)})
        return "error"


if __name__ == "__main__":
    main()
