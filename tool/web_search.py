#!/usr/bin/env python3
import time
import re
from typing import List, Tuple
from urllib.parse import urlencode, urlparse, parse_qs, unquote

import requests

from util.logging import get_logger, log_function_call, log_error, log_warning


logger = get_logger("web_search")


def _now() -> float:
    return time.time()


def _map_time_range(tr: str) -> str:
    m = {"day": "d", "week": "w", "month": "m", "year": "y"}
    return m.get(str(tr).lower(), "")


def _build_ddg_lite_url(query: str, time_range: str, safe_mode: bool) -> str:
    params = {"q": query}
    df = _map_time_range(time_range)
    if df:
        params["df"] = df
    if safe_mode:
        params["kp"] = "1"
    return "https://lite.duckduckgo.com/lite/?" + urlencode(params)


def _extract_results_from_ddg_lite(html: str, limit: int) -> List[Tuple[str, str, str]]:
    results: List[Tuple[str, str, str]] = []
    blocks = re.split(r"<tr[^>]*>", html, flags=re.I)
    for b in blocks:
        m = re.search(
            r"<a[^>]+href=\"([^\"]+)\"[^>]*>(.*?)</a>", b, flags=re.I | re.S)
        if not m:
            continue
        href = m.group(1)
        title_raw = m.group(2)
        q = urlparse(href).query
        qs = parse_qs(q)
        target = qs.get("uddg", [""])[0] or href
        url = unquote(target)
        title = re.sub(r"<[^>]+>", "", title_raw)
        if not url.lower().startswith(("http://", "https://")):
            continue
        snip_match = re.search(
            r"</a>\s*(?:<br\s*/?>)?\s*([^<]{0,400})", b, flags=re.I)
        snippet = snip_match.group(1).strip() if snip_match else ""
        snippet = re.sub(r"\s+", " ", snippet)[:500]
        results.append((title.strip(), url.strip(), snippet))
        if len(results) >= limit:
            break
    return results


def web_search(query: str, max_results: int = 5, time_range: str = "any", safe_mode: bool = True) -> str:
    try:
        log_function_call("web_search", {"query": query, "max_results": max_results,
                          "time_range": time_range, "safe_mode": safe_mode}, logger)
        if not isinstance(query, str) or not query.strip():
            return "=== WEB SEARCH ERROR ===\nQuery: \nReason: empty_query\n=== WEB SEARCH END ==="
        limit = max(1, min(int(max_results) if isinstance(
            max_results, int) else 5, 10))
        start = _now()
        results: List[Tuple[str, str, str]] = []

        try:
            try:
                from ddgs import DDGS  # type: ignore
            except Exception:
                from duckduckgo_search import DDGS  # type: ignore
            ddg_safesearch = "moderate" if safe_mode else "off"
            ddg_timelimit = _map_time_range(time_range) or None
            with DDGS() as ddgs:
                for i, res in enumerate(ddgs.text(query.strip(), safesearch=ddg_safesearch, timelimit=ddg_timelimit, max_results=limit)):
                    if _now() - start >= 60:
                        break
                    title = (res.get("title") or "").strip()
                    url_res = (res.get("href") or "").strip()
                    snippet = re.sub(
                        r"\s+", " ", (res.get("body") or "")).strip()[:500]
                    if url_res.lower().startswith(("http://", "https://")):
                        results.append((title, url_res, snippet))
                    if len(results) >= limit:
                        break
        except Exception as e:
            log_warning(f"duckduckgo_search primary failed: {str(e)}", logger)

        if not results and _now() - start < 60:
            session = requests.Session()
            session.headers.update(
                {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) LyneWebSearch/1.0"})
            url = _build_ddg_lite_url(query.strip(), time_range, safe_mode)
            try:
                r = session.get(url, timeout=12)
                if r.status_code == 200 and r.text:
                    results = _extract_results_from_ddg_lite(r.text, limit)
                elif r.status_code in (403, 429):
                    log_warning(f"DDG blocked status {r.status_code}", logger)
            except requests.RequestException as e:
                log_warning(f"DDG request failed: {str(e)}", logger)
            if not results and _now() - start < 60:
                try:
                    time.sleep(0.8)
                    r2 = session.get(url, timeout=10)
                    if r2.status_code == 200 and r2.text:
                        results = _extract_results_from_ddg_lite(
                            r2.text, limit)
                except requests.RequestException as e:
                    log_warning(f"Retry failed: {str(e)}", logger)

        total_elapsed = _now() - start
        if total_elapsed >= 60 and not results:
            return f"=== WEB SEARCH TIMEOUT (60s) ===\nQuery: {query}\n=== WEB SEARCH END ==="
        if not results:
            return f"=== WEB SEARCH NO RESULTS ===\nQuery: {query}\n=== WEB SEARCH END ==="
        lines = []
        lines.append("=== WEB SEARCH START ===")
        lines.append(f"Query: {query}")
        lines.append(f"Found: {len(results)}")
        for i, (title, url_res, snippet) in enumerate(results, 1):
            lines.append("=== SEARCH RESULT START ===")
            lines.append(f"Rank: {i}")
            lines.append(f"Title: {title}")
            lines.append(f"URL: {url_res}")
            lines.append(f"Snippet: {snippet}")
            lines.append("=== SEARCH RESULT END ===")
        lines.append("=== WEB SEARCH END ===")
        return "\n".join(lines)
    except Exception as e:
        log_error(e, "web_search failed", logger)
        return f"=== WEB SEARCH ERROR ===\nQuery: {query}\nReason: {str(e)}\n=== WEB SEARCH END ==="
