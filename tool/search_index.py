import time
import difflib
from typing import List, Dict, Union

try:
    from rapidfuzz import fuzz as _rf_fuzz  # type: ignore
except Exception:  # pragma: no cover
    _rf_fuzz = None
from pathlib import Path

from util.logging import get_logger, log_function_call, log_error, log_success
from util.filesystem_indexer import FileSystemIndexer

logger = get_logger("search_index")


def search_index(query: str, limit: int = 25) -> Union[List[Dict[str, str]], str]:
    """
    Fuzzy NAME search for files and folders using Lyne's local index.

    Args:
        query: File or folder name (or partial), case-insensitive
        limit: Maximum number of results to return (default 25, capped at 100)

    Returns:
        Either a list of entries { name, path, type } or a structured message string on error/no results.
    """
    start_ts = time.time()
    try:
        log_function_call(
            "search_index",
            {
                "query": query,
                "limit": limit,
            },
            logger,
        )

        if not isinstance(query, str) or not query.strip():
            return "SEARCH INDEX ERROR: Query must be a non-empty string."
        query_norm = query.strip()
        max_results = max(
            1, min(int(limit) if isinstance(limit, int) else 25, 100))

        project_path = str(Path.cwd())
        indexer = FileSystemIndexer(project_path)

        loaded = False
        try:
            loaded = indexer.load_index()
        except Exception:
            loaded = False

        if not loaded:
            try:
                indexer.build_index()
                loaded = indexer.load_index()
            except Exception:
                loaded = False
        if not loaded:
            return (
                "SEARCH INDEX ERROR: Failed to load or build the index. "
                "This may indicate permission issues or an inaccessible project path."
            )

        partial_deadline = 55.0

        results: List[Dict[str, str]] = []
        try:
            files = indexer.fuzzy_find_files(query_norm, limit=max_results * 2)
        except Exception:
            files = []

        if time.time() - start_ts > partial_deadline:
            files = files[: max_results]
            if files:
                return [
                    {"name": f.get("name", ""), "path": f.get(
                        "path", ""), "type": "file"}
                    for f in files[: max_results]
                ]
            return (
                f"NO RESULTS: Query '{query_norm}' returned no matches before timeout. "
                "Tip: try a shorter term or a distinctive substring."
            )

        try:
            folders = indexer.fuzzy_find_folders(
                query_norm, limit=max_results * 2)
        except Exception:
            folders = []

        def score_item(name: str) -> float:
            try:
                ql = query_norm.lower()
                nl = (name or "").lower()
                if not nl:
                    return 0.0
                if _rf_fuzz is not None:
                    ratio = _rf_fuzz.WRatio(ql, nl) / 100.0
                else:
                    ratio = difflib.SequenceMatcher(a=ql, b=nl).ratio()
                if ql in nl:
                    ratio = min(1.0, max(ratio, 0.4) + 0.2)
                return ratio
            except Exception:
                return 0.0

        combined_scored = []
        seen_paths = set()

        for f in files:
            p = f.get("path", "")
            n = f.get("name", "")
            if p and p not in seen_paths:
                s = score_item(n)
                if s >= 0.4:
                    seen_paths.add(p)
                    combined_scored.append(
                        (s, {"name": n, "path": p, "type": "file"}))

        for d in folders:
            p = d.get("path", "")
            n = d.get("name", "")
            if p and p not in seen_paths:
                s = score_item(n)
                if s >= 0.4:
                    seen_paths.add(p)
                    combined_scored.append(
                        (s, {"name": n, "path": p, "type": "folder"}))

        if not combined_scored:
            return (
                f"NO RESULTS: Nothing matched query '{query_norm}' at threshold ≥ 0.4. "
                "Notes: index excludes common dirs (node_modules, .git, lynecode, time_machine). "
                "Try a shorter or alternative name variant."
            )

        combined_scored.sort(key=lambda x: x[0], reverse=True)
        topK = [entry for _, entry in combined_scored[: max_results]]
        files = [e for e in topK if e.get("type") == "file"]
        folders = [e for e in topK if e.get("type") == "folder"]

        output: List[Dict[str, str]] = []
        if files and folders:
            output.extend(files)
            output.append({"type": "separator", "text": "--- FOLDERS ---"})
            output.extend(folders)
        elif files:
            output.append({"type": "separator", "text": "--- FILES ---"})
            output.extend(files)
        else:
            output.append({"type": "separator", "text": "--- FOLDERS ---"})
            output.extend(folders)

        log_success(f"search_index returned {len(topK)} results", logger)
        return output

    except Exception as e:
        log_error(e, "search_index failed", logger)
        return []
