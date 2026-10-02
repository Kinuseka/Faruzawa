"""Provider-agnostic upstream fetch and HLS playlist hosting (rewrite rules live in API adapters)."""

from __future__ import annotations

from collections.abc import Iterator

from API.registry import hls_proxy, _strict_headers
from constants import Constants
from essentials import cache_session
from loguru import logger
import requests.exceptions

log = logger.bind(name="CFSession")

UPSTREAM_TIMEOUT_SEC = 180
SEGMENT_READ_CHUNK = 65536
PLAYLIST_PEEK_BYTES = 8192


def _request_headers(url: str, strict_mode: bool) -> dict:
    if strict_mode:
        return dict(_strict_headers())
    adapter = hls_proxy()
    return dict(adapter.headers_for_url(url) or {})


def fetch_upstream(url: str, strict_mode=False):
    headers = _request_headers(url, strict_mode)
    try:
        resp = cache_session.VideoHandlerSession.get(
            url, headers=headers, timeout=UPSTREAM_TIMEOUT_SEC
        )
        resp.raise_for_status()
        return resp
    except requests.exceptions.RequestException:
        log.exception("Upstream fetch failed for streaming proxy")
        return None
    except Exception:
        log.exception("Unknown error during streaming proxy fetch")
        return None


def open_upstream_segment_stream(url: str, strict_mode=False):
    headers = _request_headers(url, strict_mode)
    try:
        resp = cache_session.VideoHandlerSession.get(
            url,
            headers=headers,
            stream=True,
            timeout=UPSTREAM_TIMEOUT_SEC,
        )
        resp.raise_for_status()
        return resp
    except requests.exceptions.RequestException:
        log.exception("Upstream segment stream open failed")
        return None
    except Exception:
        log.exception("Unknown error opening upstream segment stream")
        return None


def rewrite_master_playlist(playlist_text: str, master_url: str) -> str:
    if not Constants.hls_rewrite:
        return playlist_text
    return hls_proxy().rewrite_master_playlist(playlist_text, master_url)


def rewrite_media_playlist(playlist_text: str, playlist_url: str) -> str:
    if not Constants.hls_rewrite:
        return playlist_text
    return hls_proxy().rewrite_media_playlist(playlist_text, playlist_url)


def segment_response(upstream_resp):
    return hls_proxy().segment_response(upstream_resp)


def read_stream_head(upstream_resp, max_bytes: int = PLAYLIST_PEEK_BYTES) -> tuple[bytes, Iterator[bytes]]:
    """Return a leading prefix and an iterator that yields the full upstream body."""
    prefix_parts: list[bytes] = []
    total = 0
    raw_iter = upstream_resp.iter_content(chunk_size=SEGMENT_READ_CHUNK)

    while total < max_bytes:
        try:
            chunk = next(raw_iter)
        except StopIteration:
            break
        if not chunk:
            continue
        prefix_parts.append(chunk)
        total += len(chunk)

    prefix = b"".join(prefix_parts)

    def generate() -> Iterator[bytes]:
        try:
            if prefix:
                yield prefix
            for chunk in raw_iter:
                if chunk:
                    yield chunk
        except requests.exceptions.RequestException:
            log.exception("Upstream segment stream interrupted")
        finally:
            upstream_resp.close()

    return prefix, generate()


def playlist_text_from_stream(body_iter: Iterator[bytes]) -> str:
    return b"".join(body_iter).decode("utf-8", errors="replace")
