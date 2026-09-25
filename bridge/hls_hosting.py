"""Provider-agnostic upstream fetch and HLS playlist hosting (rewrite rules live in API adapters)."""

from __future__ import annotations

from API.registry import hls_proxy, _strict_headers
from constants import Constants
from essentials.cache_session import VideoHandlerSession
from loguru import logger
import requests.exceptions

log = logger.bind(name="CFSession")
_session = VideoHandlerSession

def fetch_upstream(url: str, strict_mode=False):
    adapter = hls_proxy()
    if strict_mode:
        headers = _strict_headers()
    else:
        headers = dict(adapter.headers_for_url(url) or {})
    try:
        resp = _session.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        return resp
    except requests.exceptions.RequestException:
        log.exception("Upstream fetch failed for streaming proxy")
        return None
    except Exception:
        log.exception("Unknown error during streaming proxy fetch")
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
