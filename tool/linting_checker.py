from pathlib import Path
from util.logging import get_logger, log_function_call, log_error, log_success, log_warning
import subprocess
import json
import asyncio

logger = get_logger("linting_checker")


def detect_language(file_path: str) -> str:
    p = Path(file_path)
    extension = p.suffix.lower()

    language_map = {
        '.py': 'python',
        '.js': 'javascript',
        '.c': 'c',
        '.cpp': 'cpp',
        '.cc': 'cpp',
        '.cxx': 'cpp',
        '.h': 'c',
        '.hpp': 'cpp',
        '.sql': 'sql'
    }

    return language_map.get(extension, 'unknown')


def run_pylint(file_path: str) -> dict:
    try:
        result = subprocess.run([
            'pylint', file_path, '--output-format=json', '--disable=C,R,W0613'
        ], capture_output=True, text=True, timeout=120)

        if result.returncode in [0, 6]:
            return {"status": "clean", "issues": []}

        if result.returncode in [1, 2, 32]:
            try:
                if result.stdout.strip():
                    issues = json.loads(result.stdout)
                    return {
                        "status": "issues_found",
                        "issues": [{
                            "line": issue.get("line", 0),
                            "column": issue.get("column", 0),
                            "severity": issue.get("type", "unknown"),
                            "message": issue.get("message", ""),
                            "rule": issue.get("message-id", "")
                        } for issue in issues if issue.get("type") != "info"]
                    }
                else:
                    return {"status": "clean", "issues": []}
            except json.JSONDecodeError:
                return {"status": "error", "issues": [], "error": f"Failed to parse pylint output: {result.stdout[:200]}"}

        if result.returncode == 4:

            try:
                if result.stdout.strip():
                    issues = json.loads(result.stdout)
                    if issues:
                        return {
                            "status": "issues_found",
                            "issues": [{
                                "line": issue.get("line", 0),
                                "column": issue.get("column", 0),
                                "severity": issue.get("type", "unknown"),
                                "message": issue.get("message", ""),
                                "rule": issue.get("message-id", "")
                            } for issue in issues if issue.get("type") != "info"]
                        }
                return {"status": "clean", "issues": []}
            except json.JSONDecodeError:
                return {"status": "error", "issues": [], "error": f"Pylint error: {result.stderr[:200] or 'Unknown pylint error'}"}

        return {"status": "error", "issues": [], "error": f"Pylint returned code {result.returncode}: {result.stderr[:200] or 'Unknown error'}"}

    except subprocess.TimeoutExpired:
        return {"status": "error", "issues": [], "error": "Pylint timed out"}
    except FileNotFoundError:
        return {"status": "error", "issues": [], "error": "Pylint not found. Please install pylint."}
    except Exception as e:
        return {"status": "error", "issues": [], "error": str(e)}


def run_cppcheck(file_path: str) -> dict:
    try:

        detected_lang = detect_language(file_path)

        if detected_lang == 'c':
            language_flag = '--language=c'
        else:

            language_flag = '--language=c++'

        result = subprocess.run([
            'cppcheck', file_path, '--enable=all', language_flag
        ], capture_output=True, text=True, timeout=120)

        issues = []

        error_lines = result.stderr.split('\n')
        for line in error_lines:

            if file_path in line and any(severity in line.lower() for severity in ['error:', 'warning:', 'style:']):

                file_start = line.find(file_path)
                if file_start != -1:

                    after_file = line[file_start + len(file_path):]

                    if after_file.startswith(':'):
                        parts = after_file[1:].split(':')
                        if len(parts) >= 4:
                            try:

                                if 'information:' in after_file.lower() and 'include file' in after_file.lower():
                                    continue

                                line_num = int(parts[0].strip())
                                column = int(parts[1].strip()) if len(
                                    parts) > 1 and parts[1].strip().isdigit() else 0
                                severity = parts[2].strip()

                                message_parts = parts[3:]
                                message = ':'.join(message_parts).strip()

                                if '[' in message and ']' in message:
                                    message = message.split('[')[0].strip()

                                issues.append({
                                    "line": line_num,
                                    "column": column,
                                    "severity": severity,
                                    "message": message,
                                    "rule": "cppcheck"
                                })
                            except (ValueError, IndexError):
                                continue
        return {
            "status": "issues_found" if issues else "clean",
            "issues": issues
        }

    except subprocess.TimeoutExpired:
        return {"status": "error", "issues": [], "error": "Cppcheck timed out"}
    except FileNotFoundError:
        return {"status": "error", "issues": [], "error": "Cppcheck not found. Please install cppcheck."}
    except Exception as e:
        return {"status": "error", "issues": [], "error": str(e)}


def run_cpplint(file_path: str) -> dict:
    try:
        result = subprocess.run([
            'cpplint', file_path
        ], capture_output=True, text=True, timeout=120)

        if result.returncode == 0:
            return {"status": "clean", "issues": []}

        if result.returncode == 1:
            lines = result.stdout.strip().split('\n')
            issues = []

            for line in lines:
                if ':' in line:
                    parts = line.split(':', 4)
                    if len(parts) >= 4:
                        try:
                            line_num = int(parts[1])
                            column = int(parts[2]) if len(parts) > 3 else 0
                            message = parts[3].strip() if len(
                                parts) > 3 else parts[-1].strip()
                            issues.append({
                                "line": line_num,
                                "column": column,
                                "severity": "warning",
                                "message": message,
                                "rule": "cpplint"
                            })
                        except ValueError:
                            continue

            return {
                "status": "issues_found" if issues else "clean",
                "issues": issues
            }

        return {"status": "error", "issues": [], "error": f"Cpplint returned code {result.returncode}: {result.stderr[:200] or 'Unknown error'}"}

    except subprocess.TimeoutExpired:
        return {"status": "error", "issues": [], "error": "Cpplint timed out"}
    except FileNotFoundError:
        return {"status": "error", "issues": [], "error": "Cpplint not found. Please install cpplint."}
    except Exception as e:
        return {"status": "error", "issues": [], "error": str(e)}


def run_pyjslint(file_path: str) -> dict:
    try:
        result = subprocess.run([
            'python', '-m', 'pyjslint', file_path
        ], capture_output=True, text=True, timeout=120)

        if result.returncode == 0:
            return {"status": "clean", "issues": []}

        if result.returncode == 1:
            lines = result.stderr.strip().split('\n')
            issues = []

            for line in lines:
                if file_path in line and ('error' in line.lower() or 'warning' in line.lower()):
                    parts = line.split(':')
                    if len(parts) >= 3:
                        try:
                            line_num = int(parts[1])
                            message = ':'.join(parts[2:]).strip()
                            severity = "error" if "error" in message.lower() else "warning"
                            issues.append({
                                "line": line_num,
                                "column": 0,
                                "severity": severity,
                                "message": message,
                                "rule": "jslint"
                            })
                        except ValueError:
                            continue

            return {
                "status": "issues_found" if issues else "clean",
                "issues": issues
            }

        return {"status": "error", "issues": [], "error": f"Pyjslint returned code {result.returncode}: {result.stderr[:200] or 'Unknown error'}"}

    except subprocess.TimeoutExpired:
        return {"status": "error", "issues": [], "error": "Pyjslint timed out"}
    except FileNotFoundError:
        return {"status": "error", "issues": [], "error": "Pyjslint not found. Please install pyjslint."}
    except Exception as e:
        return {"status": "error", "issues": [], "error": str(e)}


def run_sqlfluff(file_path: str) -> dict:
    try:
        result = subprocess.run([
            'sqlfluff', 'lint', file_path, '--format=json', '--dialect=ansi'
        ], capture_output=True, text=True, timeout=120)

        if result.returncode == 0:
            return {"status": "clean", "issues": []}

        if result.returncode == 1:
            try:
                data = json.loads(result.stdout)
                issues = []

                for item in data:
                    if 'violations' in item:
                        for violation in item['violations']:
                            issues.append({
                                "line": violation.get("start_line_no", 0),
                                "column": violation.get("start_line_pos", 0),
                                "severity": violation.get("code", "unknown"),
                                "message": violation.get("description", ""),
                                "rule": violation.get("code", "")
                            })

                return {
                    "status": "issues_found" if issues else "clean",
                    "issues": issues
                }
            except json.JSONDecodeError:
                return {"status": "error", "issues": [], "error": f"Failed to parse sqlfluff output: {result.stdout[:200]}"}

        return {"status": "error", "issues": [], "error": f"Sqlfluff returned code {result.returncode}: {result.stderr[:200] or 'Unknown error'}"}

    except subprocess.TimeoutExpired:
        return {"status": "error", "issues": [], "error": "Sqlfluff timed out"}
    except FileNotFoundError:
        return {"status": "error", "issues": [], "error": "Sqlfluff not found. Please install sqlfluff."}
    except Exception as e:
        return {"status": "error", "issues": [], "error": str(e)}


async def process_single_file(file_path: str) -> dict:
    """Process a single file for linting"""
    try:
        p = Path(file_path)

        if not p.is_file():
            return {
                "file_path": file_path,
                "status": "error",
                "message": f"File not found: {file_path}",
                "issues": []
            }

        language = detect_language(file_path)

        if language == "unknown":
            return {
                "file_path": file_path,
                "status": "error",
                "message": f"Unsupported file type: {p.suffix}",
                "issues": []
            }

        linter_result = None

        if language == "python":
            linter_result = await asyncio.to_thread(run_pylint, file_path)
        elif language in ["c", "cpp"]:
            linter_result = await asyncio.to_thread(run_cppcheck, file_path)
            if linter_result["status"] == "error":
                linter_result = await asyncio.to_thread(run_cpplint, file_path)
        elif language == "javascript":
            linter_result = await asyncio.to_thread(run_pyjslint, file_path)
        elif language == "sql":
            linter_result = await asyncio.to_thread(run_sqlfluff, file_path)

        if linter_result is None:
            return {
                "file_path": file_path,
                "status": "error",
                "message": f"No linter available for {language}",
                "issues": []
            }

        result = {
            "file_path": file_path,
            "status": linter_result["status"],
            "issues": linter_result.get("issues", [])
        }

        if linter_result["status"] == "error":
            result["message"] = linter_result.get("error", "Unknown error")
        elif linter_result["status"] == "clean":
            result[
                "message"] = f"The file looks great, according to current analysis there are no linting issues in this {file_path}"
        else:
            result["message"] = f"Found {len(linter_result['issues'])} issue(s)"

        return result

    except Exception as e:
        return {
            "file_path": file_path,
            "status": "error",
            "message": str(e),
            "issues": []
        }


def linting_checker(file_paths) -> list:
    """
    Check code quality issues in multiple files using appropriate linters for each language.

    Args:
        file_paths: Single file path (str) or list of file paths (max 10 files processed)

    Returns:
        List of linting results for each file with separators
    """
    try:
        log_function_call("linting_checker", {
                          'file_paths': file_paths}, logger)

        if isinstance(file_paths, str):
            file_paths = [file_paths]

        if not isinstance(file_paths, list):
            return [{
                "file_path": "unknown",
                "status": "error",
                "message": "file_paths must be a string or list of strings",
                "issues": []
            }]

        if len(file_paths) > 10:
            file_paths = file_paths[:10]
            log_warning(
                f"Limited to processing first 10 files out of {len(file_paths)} provided", logger)

        async def process_all():
            tasks = [process_single_file(fp) for fp in file_paths]
            return await asyncio.gather(*tasks)

        results = asyncio.run(process_all())

        final_results = []
        for result in results:
            final_results.append(result)
            final_results.append({
                "separator": f"------- linting result for {result['file_path']} -------"
            })

        log_success(f"Linting completed for {len(file_paths)} file(s)", logger)
        return final_results

    except Exception as e:
        log_error(e, "Error in linting_checker", logger)
        return [{
            "file_path": "unknown",
            "status": "error",
            "message": str(e),
            "issues": []
        }]
