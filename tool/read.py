from pathlib import Path
from util.logging import get_logger, log_function_call, log_error, log_success

logger = get_logger("read")


def is_likely_text_file(file_path: Path) -> bool:
    """
    Checks if a file is likely text-based by reading its first few bytes.
    Returns False if it detects null bytes, which are common in binary files.
    """
    try:
        import os
        file_size = os.path.getsize(file_path)

        if file_size == 0:
            return True

        import mmap
        with open(file_path, 'rb') as f:
            with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                chunk = mm[:512]
                if b'\x00' in chunk:
                    return False
    except Exception:
        return False
    return True


def fetch_content(file_path: str, start_line: int = 1, end_line: int = 200) -> str:
    """
    Fetches content from a text-based file, preserving indentation and structure.

    Args:
        file_path: Path to the file to read
        start_line: Starting line number (1-indexed, default: 1)
        end_line: Ending line number (inclusive, default: 200)

    Returns:
        The file content as a string, or None if the file cannot be read
    """
    try:
        log_function_call("fetch_content", {
            'file_path': file_path,
            'start_line': start_line,
            'end_line': end_line
        }, logger)

        p = Path(file_path)

        if not p.is_file():
            log_error(
                Exception(f"File not found: {file_path}"), "File not found", logger)
            return None

        if not is_likely_text_file(p):
            log_error(Exception(
                f"Binary file detected: {file_path}"), "Binary file cannot be read", logger)
            return None

        if start_line < 1 or end_line < start_line:
            log_error(Exception("Invalid line range"),
                      "Invalid line range", logger)
            return None

        import os

        file_path_str = str(p)
        file_size = os.path.getsize(file_path_str)

        if file_size < 102400:
            with open(p, 'r', encoding='utf-8', errors='ignore') as f:
                all_lines = f.readlines()
        else:
            with open(p, 'r', encoding='utf-8', errors='ignore') as f:
                all_lines = []
                for i, line in enumerate(f, 1):
                    if i > end_line + 100:
                        break
                    all_lines.append(line)

        total_lines = len(all_lines)
        if file_size >= 102400 and total_lines <= end_line + 100:
            with open(p, 'r', encoding='utf-8', errors='ignore') as f:
                all_lines = f.readlines()
            total_lines = len(all_lines)

        if total_lines == 0:
            return f"FILE STATUS: The file '{file_path}' exists but is completely empty (no lines, size is 0 bytes). This is likely a fresh/empty file, no need to call fetch_content again on this path unless content is added later."

        start_index = start_line - 1

        if start_index >= total_lines:
            actual_start = max(0, total_lines - 20)
            start_index = actual_start
            end_index = total_lines

            warning_message = (
                f"\n Requested start line {start_line} is beyond file end (file has {total_lines} lines). "
                f"Providing lines {actual_start + 1}-{total_lines} instead (last 20 lines of the file).\n"
            )

            logger.info(f"Line range fallback: {warning_message.strip()}")

        end_index = min(end_line, total_lines)
        content_slice = all_lines[start_index:end_index]

        if not content_slice:
            lines_remaining = total_lines - start_line + 1
            if lines_remaining <= 0:
                return f"\n{'='*80}\n📖 END OF FILE REACHED - No more content to read\n{'='*80}"
            else:
                return f"\n{'='*60}\n📖 NO CONTENT IN REQUESTED RANGE\n• Requested lines: {start_line}-{end_line}\n• Total lines in file: {total_lines}\n• Lines remaining: {lines_remaining}\n• To read more: call with start_line={start_line}\n{'='*60}"

        import io

        content_builder = io.StringIO()
        for line in content_slice:
            content_builder.write(line)
        content = content_builder.getvalue()
        content_builder.close()

        actual_end = min(end_line, total_lines)
        lines_read = len(content_slice)

        if actual_end >= total_lines:
            progress_info = f"\n{'='*80}\n📖 FILE FULLY READ - All {total_lines} lines displayed\n{'='*80}"
        else:
            lines_remaining = total_lines - actual_end
            progress_info = f"\n{'='*60}\n📖 FILE PARTIALLY READ\n• Lines displayed: {start_line}-{actual_end} ({lines_read} lines)\n• Total lines in file: {total_lines}\n• Lines remaining: {lines_remaining}\n{'='*60}"

        content += progress_info

        if start_index != start_line - 1:
            actual_start_line = actual_start + 1
            log_success(
                f"Fallback read: {len(content_slice)} lines from {file_path} (lines {actual_start_line}-{actual_end} of {total_lines} - original request was {start_line}-{end_line})", logger)
            content = warning_message + content
        else:
            log_success(
                f"Successfully read {len(content_slice)} lines from {file_path} (lines {start_line}-{actual_end} of {total_lines})", logger)
        return content
    except Exception as e:
        log_error(e, f"Error reading file {file_path}", logger)
        return None
