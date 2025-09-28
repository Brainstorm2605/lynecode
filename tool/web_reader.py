#!/usr/bin/env python3
import time
import re
from urllib.parse import urlparse
from typing import Optional

import requests
from bs4 import BeautifulSoup

from util.logging import get_logger, log_function_call, log_error, log_warning

try:
    from curl_cffi import requests as curl_requests  # type: ignore
    HAS_CURL = True
except Exception:
    HAS_CURL = False

try:
    import trafilatura  # type: ignore
    HAS_TRAFILATURA = True
except Exception:
    HAS_TRAFILATURA = False

try:
    from readability import Document  # type: ignore
    HAS_READABILITY = True
except Exception:
    HAS_READABILITY = False


logger = get_logger("web_reader")


def _now() -> float:
    return time.time()


def _is_http_url(u: str) -> bool:
    try:
        p = urlparse(u)
        return p.scheme in {"http", "https"}
    except Exception:
        return False


def _clean_text(text: str) -> str:
    t = re.sub(r"\s+", " ", text or "").strip()
    return t


def _extract_meta_refresh_target(html: str, base_url: str) -> Optional[str]:
    try:
        soup = BeautifulSoup(html or "", "html.parser")
        meta = soup.find(
            "meta", attrs={"http-equiv": lambda v: v and v.lower() == "refresh"})
        if not meta:
            return None
        content = meta.get("content") or meta.get("CONTENT") or ""
        m = re.search(r"url\s*=\s*([^;]+)", content, flags=re.I)
        if not m:
            return None
        target = m.group(1).strip().strip('"\'')
        from urllib.parse import urljoin
        target_abs = urljoin(base_url, target)
        if _is_http_url(target_abs):
            return target_abs
        return None
    except Exception:
        return None


def _find_first_absolute_link(html: str) -> Optional[str]:
    try:
        soup = BeautifulSoup(html or "", "html.parser")
        for a in soup.find_all("a", href=True):
            href = a.get("href")
            if href and _is_http_url(href):
                return href
        return None
    except Exception:
        return None


def _looks_like_redirect_page(title: str, text: str) -> bool:
    t = (title or "") + " " + (text or "")
    tl = t.lower()
    return ("redirect" in tl) or ("you are being redirected" in tl) or ("you're being redirected" in tl)


def _extract_main_text(html: str) -> str:
    if not html:
        return ""
    if HAS_TRAFILATURA:
        try:
            txt = trafilatura.extract(html) or ""
            txt = _clean_text(txt)
            if len(txt) >= 200:
                return txt
        except Exception:
            pass
    if HAS_READABILITY:
        try:
            doc = Document(html)
            summ_html = doc.summary(html_partial=True)
            soup = BeautifulSoup(summ_html, "html.parser")
            for t in soup(["script", "style", "noscript"]):
                t.decompose()
            txt = _clean_text(soup.get_text(" "))
            if len(txt) >= 200:
                return txt
        except Exception:
            pass
    try:
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        article = soup.find("article")
        if article:
            return _clean_text(article.get_text(" "))
        main = soup.find("main")
        if main:
            return _clean_text(main.get_text(" "))
        body = soup.find("body") or soup
        return _clean_text(body.get_text(" "))
    except Exception:
        return ""


def read_web_page(url: str, max_chars: int = 8000, include_links: bool = False) -> str:
    try:
        log_function_call("read_web_page", {
                          "url": url, "max_chars": max_chars, "include_links": include_links}, logger)
        if not isinstance(url, str) or not url.strip() or not _is_http_url(url):
            return "=== WEB PAGE ERROR ===\nURL: \nReason: invalid_url\n=== WEB PAGE END ==="
        cap = max(1000, min(int(max_chars) if isinstance(
            max_chars, int) else 8000, 20000))
        start = _now()
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9"
        }
        r = None
        if HAS_CURL:
            try:
                r = curl_requests.get(
                    url, timeout=15, allow_redirects=True, impersonate="chrome", headers=headers)
            except Exception as e:
                log_warning(f"curl_cffi fetch failed: {str(e)}", logger)
                r = None
        if r is None:
            session = requests.Session()
            session.headers.update(headers)
            try:
                r = session.get(url, timeout=15, allow_redirects=True)
            except requests.RequestException as e:
                log_warning(f"Fetch failed: {str(e)}", logger)
                return f"=== WEB PAGE ERROR ===\nURL: {url}\nReason: fetch_failed\n=== WEB PAGE END ==="
        elapsed = _now() - start
        if elapsed >= 60:
            return f"=== WEB PAGE TIMEOUT (60s) ===\nURL: {url}\n=== WEB PAGE END ==="
        if r.status_code in (403, 429) and _now() - start < 60:
            try:
                referer_headers = dict(headers)
                referer_headers["Referer"] = "https://www.google.com/"
                if HAS_CURL:
                    r = curl_requests.get(
                        url, timeout=15, allow_redirects=True, impersonate="chrome", headers=referer_headers)
                else:
                    r = requests.get(
                        url, timeout=15, allow_redirects=True, headers=referer_headers)
            except Exception:
                pass
        ct = (r.headers.get("Content-Type") or "").lower()
        if r.status_code != 200:
            return f"=== WEB PAGE ERROR ===\nURL: {url}\nReason: http_{r.status_code}\n=== WEB PAGE END ==="

        redirect_note = None
        if "html" in ct:
            target = _extract_meta_refresh_target(r.text, url)
            if not target:
                try:
                    soup_tmp = BeautifulSoup(r.text or "", "html.parser")
                    title_tmp = _clean_text(
                        (soup_tmp.title.string if soup_tmp.title else "") or "")
                    body_txt = _clean_text(soup_tmp.get_text(" "))
                except Exception:
                    title_tmp, body_txt = "", ""
                if _looks_like_redirect_page(title_tmp, body_txt):
                    target = _find_first_absolute_link(r.text)
            if target and _is_http_url(target) and (_now() - start) < 58:
                try:
                    if HAS_CURL:
                        r2 = curl_requests.get(target, timeout=max(5, int(
                            60 - (_now() - start))), allow_redirects=True, impersonate="chrome", headers=headers)
                    else:
                        r2 = requests.get(target, timeout=max(
                            5, int(60 - (_now() - start))), allow_redirects=True, headers=headers)
                    if r2.status_code == 200 and (r2.headers.get("Content-Type", "").lower().find("html") != -1):
                        r = r2
                        url = target
                        redirect_note = f"Note: Followed redirect to {target}"
                except Exception:
                    pass
        if "pdf" in ct or url.lower().endswith(".pdf"):
            return f"=== WEB PAGE START ===\nURL: {url}\nTitle: \nNote: Non-HTML content detected (e.g., PDF). Extracted text may be partial.\nContent:\n\n=== WEB PAGE END ==="
        html = r.text or ""
        try:
            soup = BeautifulSoup(html, "html.parser")
            title = _clean_text(
                (soup.title.string if soup.title else "") or "")
        except Exception:
            title = ""
        text = _extract_main_text(html)[:cap]
        out_lines = ["=== WEB PAGE START ===",
                     f"URL: {url}", f"Title: {title}"]
        if redirect_note:
            out_lines.append(redirect_note)
        out_lines += ["Content:", text, "=== WEB PAGE END ==="]
        if include_links:
            try:
                soup = BeautifulSoup(html, "html.parser")
                links = []
                for a in soup.find_all("a", href=True):
                    href = a.get("href")
                    if href and _is_http_url(href):
                        txt = _clean_text(a.get_text(" "))
                        links.append((txt, href))
                        if len(links) >= 20:
                            break
                if links:
                    block = ["Links (up to 20):"]
                    for t, h in links:
                        block.append(f"- {t} — {h}")
                    out_lines = out_lines[:-1] + \
                        block + ["=== WEB PAGE END ==="]
            except Exception:
                pass
        return "\n".join(out_lines)
    except Exception as e:
        log_error(e, "read_web_page failed", logger)
        return f"=== WEB PAGE ERROR ===\nURL: {url}\nReason: {str(e)}\n=== WEB PAGE END ==="
