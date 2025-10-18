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


MAX_FULL_LINES = 2000
MAX_FULL_CHARS = 32000


def fetch_content(
    file_path: str,
    start_line: int = 1,
    end_line: int | None = 200,
    full_file: bool = False,
) -> str:
    """
    Fetches content from a text-based file, preserving indentation and structure.

    Args:
        file_path: Path to the file to read
        start_line: Starting line number (1-indexed, default: 1)
        end_line: Ending line number (inclusive, default: 200)
        full_file: When True, fetches the full file (up to 2000 lines / 32000 chars) regardless of end_line

    Returns:
        The file content as a string, or None if the file cannot be read
    """
    try:
        log_function_call(
            "fetch_content",
            {
                'file_path': file_path,
                'start_line': start_line,
                'end_line': end_line,
                'full_file': full_file,
            },
            logger,
        )

        if full_file:
            start_line = 1
            end_line = None

        p = Path(file_path)

        if not p.is_file():
            log_error(
                Exception(f"File not found: {file_path}"), "File not found", logger)
            return None

        if not is_likely_text_file(p):
            log_error(Exception(
                f"Binary file detected: {file_path}"), "Binary file cannot be read", logger)
            return None

        if start_line < 1:
            log_error(Exception("Invalid line range"),
                      "Invalid line range", logger)
            return None

        import os

        file_path_str = str(p)
        file_size = os.path.getsize(file_path_str)

        small_file_threshold = 2 * 1024 * 1024  # 2 MB

        if file_size < small_file_threshold:
            with open(p, 'r', encoding='utf-8', errors='ignore') as f:
                all_lines = f.readlines()
        else:
            with open(p, 'r', encoding='utf-8', errors='ignore') as f:
                all_lines = []
                for i, line in enumerate(f, 1):
                    if full_file and i > MAX_FULL_LINES + 50:
                        break
                    if not full_file and end_line is not None and i > end_line + 100:
                        break
                    all_lines.append(line)

        total_lines = len(all_lines)
        if (
            file_size >= small_file_threshold
            and not full_file
            and end_line is not None
            and total_lines <= end_line + 100
        ):
            with open(p, 'r', encoding='utf-8', errors='ignore') as f:
                all_lines = f.readlines()
            total_lines = len(all_lines)

        if total_lines == 0:
            return (
                f"FILE STATUS: The file '{file_path}' exists but is completely empty (no lines, size is 0 bytes). "
                "This is likely a fresh/empty file, no need to call fetch_content again on this path unless content is added later."
            )

        limit_lines = full_file or (start_line == 1 and end_line is None)

        start_index = start_line - 1
        actual_start_line = start_index + 1
        warning_message = ""

        if start_index >= total_lines:
            actual_start = max(0, total_lines - 20)
            start_index = actual_start
            actual_start_line = actual_start + 1
            end_index = total_lines

            warning_message = (
                f"\n Requested start line {start_line} is beyond file end (file has {total_lines} lines). "
                f"Providing lines {actual_start + 1}-{total_lines} instead (last 20 lines of the file).\n"
            )

            logger.info(f"Line range fallback: {warning_message.strip()}")
        else:
            if limit_lines:
                end_index = min(total_lines, start_index + MAX_FULL_LINES)
            else:
                end_line_value = end_line if end_line is not None else start_line + 199
                if end_line_value < start_line:
                    log_error(Exception("Invalid line range"),
                              "Invalid line range", logger)
                    return None
                end_index = min(end_line_value, total_lines)

        content_slice = all_lines[start_index:end_index]

        if not content_slice:
            lines_remaining = total_lines - actual_start_line + 1
            if lines_remaining <= 0:
                return (
                    f"\n{'='*80}\n📖 END OF FILE REACHED - No more content to read\n{'='*80}"
                )
            return (
                f"\n{'='*60}\n📖 NO CONTENT IN REQUESTED RANGE\n"
                f"• Requested lines: {start_line}-{end_line}\n"
                f"• Total lines in file: {total_lines}\n"
                f"• Lines remaining: {lines_remaining}\n"
                f"• To read more: call with start_line={start_line}\n{'='*60}"
            )

        import io

        content_builder = io.StringIO()
        char_count = 0
        lines_written = 0
        for line in content_slice:
            if limit_lines and char_count >= MAX_FULL_CHARS:
                break
            content_builder.write(line)
            char_count += len(line)
            lines_written += 1
        content = content_builder.getvalue()
        content_builder.close()

        actual_end = actual_start_line + lines_written - 1

        guidance_message = ""
        if limit_lines and (actual_end < total_lines or lines_written >= MAX_FULL_LINES or char_count >= MAX_FULL_CHARS):
            guidance_message = (
                f"\n==== FETCH CONTENT NOTICE ===="
                f"\nYou requested the **full file** for '{file_path}'. To protect the session, only the first {lines_written} lines (approx {char_count} characters) are returning."
                f"\nTo continue reading the file, set `full_file` to `False` and request the next range:"
                f"\n  start_line = {actual_end + 1}"
                f"\n  end_line   = desired_span"
                f"\n  Total lines of the file: {total_lines}"
                f"\n==== END OF NOTICE ===="
            )

        if limit_lines and (
            actual_end >= total_lines or
            lines_written < MAX_FULL_LINES and char_count < MAX_FULL_CHARS
        ):
            progress_info = (
                f"\n{'='*80}\n📖 FILE DISPLAYED (up to {lines_written} lines, {char_count} characters)\n{'='*80}"
            )
        elif actual_end >= total_lines:
            progress_info = (
                f"\n{'='*80}\n📖 FILE FULLY READ - All {total_lines} lines displayed\n{'='*80}"
            )
        else:
            lines_remaining = total_lines - actual_end
            progress_info = (
                f"\n{'='*60}\n📖 FILE PARTIALLY READ\n"
                f"• Lines displayed: {actual_start_line}-{actual_end} ({lines_written} lines)\n"
                f"• Total lines in file: {total_lines}\n"
                f"• Lines remaining: {lines_remaining}\n{'='*60}"
            )

        content += progress_info
        if guidance_message:
            content += guidance_message

        if warning_message:
            log_success(
                f"Fallback read: {lines_written} lines from {file_path} (lines {actual_start_line}-{actual_end} of {total_lines} - original request was {start_line}-{end_line})",
                logger,
            )
            content = warning_message + content
        else:
            if limit_lines:
                log_success(
                    f"Successfully read up to {lines_written} lines ({char_count} chars) from {file_path} starting at line {actual_start_line}",
                    logger,
                )
            else:
                log_success(
                    f"Successfully read {lines_written} lines from {file_path} (lines {actual_start_line}-{actual_end} of {total_lines})",
                    logger,
                )
        return content
    except Exception as e:
        log_error(e, f"Error reading file {file_path}", logger)
        return None
