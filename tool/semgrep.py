#!/usr/bin/env python3
"""
Semgrep scanning tool for Lyne.

Provides a thin wrapper around the Semgrep CLI with sensible defaults,
structured JSON parsing, timeouts, and filtering controls.
"""

import os
import json
import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from util.logging import get_logger, log_function_call, log_error, log_warning, log_success


logger = get_logger("semgrep")


def _resolve_semgrep_executable() -> Optional[str]:
    """Return the best available Semgrep executable name in PATH."""
    try:
        candidates = ["semgrep", "pysemgrep", "python -m semgrep"]
        for candidate in candidates:
            if " " in candidate:
                return candidate
            exe = shutil.which(candidate)
            if exe:
                return candidate
    except Exception:
        pass
    return None


def _build_semgrep_command(
    target_path: Path,
    config: str,
    severity: Optional[List[str]],
    timeout_sec: int,
) -> List[str]:
    """Construct the Semgrep CLI argv with filters and JSON output."""
    cmd_str = _resolve_semgrep_executable() or "semgrep"
    if cmd_str == "python -m semgrep":
        argv = ["python", "-m", "semgrep"]
    else:
        argv = [cmd_str]

    argv.extend([
        "scan",
        "--json",
        "--timeout", str(timeout_sec),
        "--no-rewrite-rule-ids",
    ])

    try:
        cpu_count = os.cpu_count() or 4
        argv.extend(["--jobs", str(cpu_count)])
    except Exception:
        pass

    if config and config.strip().lower() != "auto":
        argv.extend(["--config", config])
    else:
        argv.extend(["--config", "auto"])

    if severity:
        for sev in severity:
            level = str(sev).upper().strip()
            if level in {"INFO", "WARNING", "ERROR"}:
                argv.extend(["--severity", level])

    argv.append(str(target_path))
    return argv


def _extract_results_array(text: str) -> Optional[List[Dict[str, Any]]]:
    """Best-effort extraction of the results array from possibly truncated JSON."""
    try:
        if not text:
            return None
        key_idx = text.find('"results"')
        if key_idx == -1:
            return None

        br_start = text.find('[', key_idx)
        if br_start == -1:
            return None

        depth = 0
        for i in range(br_start, len(text)):
            ch = text[i]
            if ch == '[':
                depth += 1
            elif ch == ']':
                depth -= 1
                if depth == 0:
                    arr_text = text[br_start:i+1]
                    try:
                        return json.loads(arr_text)
                    except Exception:
                        return None
        return None
    except Exception:
        return None


def _parse_semgrep_json(stdout_text: str) -> Dict[str, Any]:
    try:
        data = json.loads(stdout_text or "{}")
    except json.JSONDecodeError:

        recovered = _extract_results_array(stdout_text)
        if recovered is not None:
            findings: List[Dict[str, Any]] = []
            for r in recovered:
                try:
                    check_id = r.get("check_id", "")
                    path = r.get("path", "")
                    start = (r.get("start") or {})
                    extra = (r.get("extra") or {})
                    findings.append({
                        "file": path,
                        "line": int(start.get("line", 0) or 0),
                        "column": int(start.get("col", 0) or 0),
                        "severity": (extra.get("severity") or "unknown").lower(),
                        "rule_id": check_id,
                        "message": extra.get("message", ""),
                        "metadata": extra.get("metadata", {}),
                        "fix": extra.get("fix", None),
                    })
                except Exception:
                    continue
            return {
                "status": "issues_found" if findings else "clean",
                "message": "Recovered partial Semgrep results",
                "findings": findings,
                "metrics": {"results_total": len(recovered)}
            }
        return {"status": "error", "message": "Failed to parse Semgrep JSON output", "findings": []}

    results = data.get("results", []) or []

    findings: List[Dict[str, Any]] = []
    for r in results:
        try:
            check_id = r.get("check_id", "")
            path = r.get("path", "")
            start = (r.get("start") or {})
            extra = (r.get("extra") or {})
            findings.append({
                "file": path,
                "line": int(start.get("line", 0) or 0),
                "column": int(start.get("col", 0) or 0),
                "severity": (extra.get("severity") or "unknown").lower(),
                "rule_id": check_id,
                "message": extra.get("message", ""),
                "metadata": extra.get("metadata", {}),
                "fix": extra.get("fix", None),
            })
        except Exception:
            continue

    return {
        "status": "issues_found" if findings else "clean",
        "message": f"Found {len(findings)} finding(s)" if findings else "No Semgrep findings",
        "findings": findings,
        "metrics": {
            "results_total": len(results),
        }
    }


def semgrep_scan(
    path: str,
    severity: Optional[List[str]] = None,
    max_results: int = 200,
    timeout_sec: int = 60
) -> Dict[str, Any]:
    """
    Run Semgrep on a file or directory and return normalized findings.

    Args:
        path: File or directory to scan.
        severity: Optional list among [INFO, WARNING, ERROR].
        max_results: Limit number of findings returned.
        timeout_sec: CLI timeout per Semgrep invocation.

    Returns:
        Dict with keys: status, message, findings (list), metrics.
    """
    try:
        log_function_call("semgrep_scan", {
            "path": path,
            "severity": severity,
            "max_results": max_results,
            "timeout_sec": timeout_sec
        }, logger)

        target = Path(path).resolve()
        if not target.exists():
            return {"status": "error", "message": f"Path does not exist: {path}", "findings": []}

        exe = _resolve_semgrep_executable()
        if not exe:
            message = "EXECUTABLE NOT FOUND: Semgrep is not available in PATH. Please install Semgrep."
            return {
                "success": False,
                "tool_name": "semgrep_scan",
                "result": {
                    "status": "error",
                    "message": message,
                    "findings": [],
                    "path": str(target),
                    "severity": severity or [],
                    "max_results": max_results
                }
            }

        argv = _build_semgrep_command(target, "auto", severity, timeout_sec)

        env = os.environ.copy()

        env.setdefault("SEMGREP_SEND_METRICS", "off")

        timed_out = False
        stdout_text = ""
        stderr_text = ""
        exit_code: Optional[int] = None
        try:
            proc = subprocess.Popen(
                argv,
                cwd=str(target if target.is_dir() else target.parent),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace',
                bufsize=1
            )

            stdout_lines: List[str] = []
            stderr_lines: List[str] = []

            def _drain(stream, sink_list):
                try:
                    for line in iter(stream.readline, ''):
                        sink_list.append(line)
                except Exception:
                    pass

            t_out = threading.Thread(target=_drain, args=(
                proc.stdout, stdout_lines)) if proc.stdout else None
            t_err = threading.Thread(target=_drain, args=(
                proc.stderr, stderr_lines)) if proc.stderr else None
            if t_out:
                t_out.daemon = True
                t_out.start()
            if t_err:
                t_err.daemon = True
                t_err.start()

            try:
                proc.wait(timeout=timeout_sec + 5)
            except subprocess.TimeoutExpired:
                timed_out = True
                try:
                    proc.terminate()
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    try:
                        proc.kill()
                    except Exception:
                        pass
                except Exception:
                    pass
            finally:

                try:
                    if t_out:
                        t_out.join(timeout=2)
                    if t_err:
                        t_err.join(timeout=2)
                except Exception:
                    pass
                try:
                    if proc.stdout:
                        proc.stdout.close()
                    if proc.stderr:
                        proc.stderr.close()
                except Exception:
                    pass

            exit_code = proc.returncode
            stdout_text = ''.join(stdout_lines)
            stderr_text = ''.join(stderr_lines)

        except FileNotFoundError:
            message = "EXECUTABLE NOT FOUND: Semgrep is not available in PATH. Please install Semgrep."
            return {
                "success": False,
                "tool_name": "semgrep_scan",
                "result": {
                    "status": "error",
                    "message": message,
                    "findings": [],
                    "path": str(target),
                    "severity": severity or [],
                    "max_results": max_results
                }
            }
        except Exception as e:
            log_error(e, "Semgrep execution failed", logger)
            return {
                "success": False,
                "tool_name": "semgrep_scan",
                "result": {
                    "status": "error",
                    "message": str(e),
                    "findings": [],
                    "path": str(target),
                    "severity": severity or [],
                    "max_results": max_results
                }
            }

        parsed = _parse_semgrep_json(stdout_text)

        findings = parsed.get("findings", [])
        if isinstance(max_results, int) and max_results > 0 and len(findings) > max_results:
            findings = findings[:max_results]

        status = parsed.get("status", "clean")
        if timed_out:
            status = "timeout"
        elif exit_code not in (0, 1, None):
            status = "error"

        if status == "timeout":
            message = f"SEMGREP TIMEOUT: Scan exceeded {timeout_sec}s. Returning {len(findings)} finding(s) collected so far."
        elif status == "error":
            stderr_first = (stderr_text or "").strip().splitlines()[:3]
            stderr_preview = " ".join(stderr_first)
            message = parsed.get("message") or (
                stderr_preview or f"Semgrep exited with code {exit_code}")
        elif findings:
            message = f"SUCCESS: Found {len(findings)} finding(s) with Semgrep."
        else:
            message = f"SUCCESS: No Semgrep findings."

        result_payload = {
            "status": status,
            "message": message,
            "findings": findings,
            "found_count": len(findings),
            "metrics": {
                "results_total": parsed.get("metrics", {}).get("results_total", len(findings)),
                "exit_code": exit_code,
                "timed_out": timed_out
            },
            "path": str(target),
            "severity": severity or [],
            "max_results": max_results
        }

        success_flag = status in {"success",
                                  "clean", "issues_found", "timeout"}
        if status == "issues_found":
            success_flag = True
        if status == "clean":
            success_flag = True
        if status == "timeout":
            success_flag = True
        if status == "success":
            success_flag = True

        log_success(
            f"Semgrep {'timed out' if timed_out else 'completed'} with {len(findings)} finding(s)", logger)
        return {
            "success": success_flag,
            "tool_name": "semgrep_scan",
            "result": result_payload
        }

    except Exception as e:
        log_error(e, "semgrep_scan unexpected failure", logger)
        return {"status": "error", "message": str(e), "findings": []}
