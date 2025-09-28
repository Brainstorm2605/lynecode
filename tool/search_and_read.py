#!/usr/bin/env python3
"""
Hybrid tool that combines grep search with file reading to get context around search results.
This tool eliminates the need for separate grep and read operations.
"""

from pathlib import Path
from .grep import grep_search
from .read import fetch_content
from util.logging import get_logger, log_function_call, log_error, log_success

logger = get_logger("search_and_read")


def search_and_read(
    pattern: str,
    path: str,
    max_results: int = 20,
    context_lines: int = 50,
    include_pattern: str = None,
    exclude_dirs: list = None
) -> list:
    """
    Search for text patterns and read context around each match in a single operation.

    Args:
        pattern: Regular expression pattern to search for
        path: Path to search in (required)
        max_results: Maximum number of results to process (default: 10)
        context_lines: Number of lines to read before and after each match (default: 50)
        include_pattern: Optional glob pattern to filter files (e.g., "*.py", "*.{js,ts}")
        exclude_dirs: List of directories to exclude from search

    Returns:
        List of dictionaries containing search results with context:
        {
            'file': str,          
            'line_number': int,
            'content': str,
            'context': str,
            'start_line': int,
            'end_line': int
        }
    """
    try:
        log_function_call("search_and_read", {
            'pattern': pattern,
            'path': path,
            'max_results': max_results,
            'context_lines': context_lines,
            'include_pattern': include_pattern,
            'exclude_dirs': exclude_dirs
        }, logger)

        search_results = grep_search(
            pattern=pattern,
            path=path,
            max_results=max_results,
            include_pattern=include_pattern,
            exclude_dirs=exclude_dirs
        )

        if not search_results:
            log_success("No search results found", logger)
            return []

        file_groups = {}
        for result in search_results[:max_results]:
            file_path = result['file']
            if file_path not in file_groups:
                file_groups[file_path] = []
            file_groups[file_path].append(result)

        results_with_context = []
        for file_path, matches in file_groups.items():
            if len(matches) == 1:

                result = matches[0]
                match_line = result['line_number']
                match_content = result['content']
                try:
                    start_line = max(1, match_line - context_lines)
                    end_line = match_line + context_lines

                    context_content = fetch_content(
                        file_path, start_line, end_line)
                    if context_content is not None:
                        enhanced_result = {
                            'file': file_path,
                            'line_number': match_line,
                            'content': match_content,
                            'context': context_content,
                            'start_line': start_line,
                            'end_line': end_line
                        }
                        results_with_context.append(enhanced_result)
                    else:
                        logger.warning(
                            f"Could not read context from {file_path}")
                        enhanced_result = {
                            'file': file_path,
                            'line_number': match_line,
                            'content': match_content,
                            'context': match_content,
                            'start_line': match_line,
                            'end_line': match_line
                        }
                        results_with_context.append(enhanced_result)
                except Exception as e:
                    log_error(
                        e, f"Error processing context for {file_path}", logger)
                    enhanced_result = {
                        'file': file_path,
                        'line_number': match_line,
                        'content': match_content,
                        'context': match_content,
                        'start_line': match_line,
                        'end_line': match_line
                    }
                    results_with_context.append(enhanced_result)
            else:
                matches.sort(key=lambda x: x['line_number'])

                processed_ranges = []
                for result in matches:
                    match_line = result['line_number']
                    match_content = result['content']

                    start_line = max(1, match_line - context_lines)
                    end_line = match_line + context_lines

                    overlapped = False
                    for prev_start, prev_end in processed_ranges:
                        if (start_line <= prev_end and end_line >= prev_start):

                            range_size = end_line - start_line
                            overlap_start = max(start_line, prev_start)
                            overlap_end = min(end_line, prev_end)
                            overlap_size = overlap_end - overlap_start

                            if overlap_size > range_size * 0.7:
                                overlapped = True
                                break

                    if not overlapped:
                        try:
                            context_content = fetch_content(
                                file_path, start_line, end_line)
                            if context_content is not None:
                                enhanced_result = {
                                    'file': file_path,
                                    'line_number': match_line,
                                    'content': match_content,
                                    'context': context_content,
                                    'start_line': start_line,
                                    'end_line': end_line
                                }
                                results_with_context.append(enhanced_result)
                                processed_ranges.append((start_line, end_line))
                            else:
                                logger.warning(
                                    f"Could not read context from {file_path} at line {match_line}")
                                enhanced_result = {
                                    'file': file_path,
                                    'line_number': match_line,
                                    'content': match_content,
                                    'context': match_content,
                                    'start_line': match_line,
                                    'end_line': match_line
                                }
                                results_with_context.append(enhanced_result)
                        except Exception as e:
                            log_error(
                                e, f"Error processing context for {file_path} at line {match_line}", logger)
                            enhanced_result = {
                                'file': file_path,
                                'line_number': match_line,
                                'content': match_content,
                                'context': match_content,
                                'start_line': match_line,
                                'end_line': match_line
                            }
                            results_with_context.append(enhanced_result)
        log_success(
            f"Successfully processed {len(results_with_context)} results with context", logger)
        return results_with_context

    except Exception as e:
        log_error(
            e, f"Error in search_and_read for pattern: {pattern}", logger)
        return []
