"""Playback resolution and watch-page context (provider-neutral facade)."""

from API import player_class
from API.HlsMetadata import parse_hls_master_media
from API.registry import external_subtitles_for_player
from bridge.catalog import catalog
from bridge import hls_hosting
from essentials.tools import encrypt
from constants import Constants
import frzw_exceptions


class Streaming:
    def __init__(self, catalog_facade) -> None:
        self._catalog = catalog_facade

    def episode_flair(self, title_flair: str, episode: str):
        series = self._catalog.series_for_flair(title_flair)
        if not series:
            return None
        return self._episode_flair_from_series(series, episode)

    def _episode_flair_from_series(self, series, episode: str):
        link = series.get_episode_link(episode)
        if not link:
            return None
        return link[episode]["episode-flair"]

    def adjacent_episodes(self, series, episode: str):
        episode_next = series.get_episode_link(episode, adjustment=1)
        if episode_next:
            episode_next = list(episode_next.keys())[0]
        episode_prev = series.get_episode_link(episode, adjustment=-1)
        if episode_prev:
            episode_prev = list(episode_prev.keys())[0]
        return episode_next, episode_prev

    def player_for_episode_flair(self, flair: str):
        return player_class()(flair)

    def sources_for_episode_flair(self, flair: str):
        player = self.player_for_episode_flair(flair)
        return player.get_streaming_data()

    def watch_context(self, title_flair: str, episode: str):
        series = self._catalog.series_for_flair(title_flair)
        if not series:
            return None
        full_flair = self._episode_flair_from_series(series, episode)
        if not full_flair:
            return None
        episode_next, episode_prev = self.adjacent_episodes(series, episode)
        anime_details = series.get_anime_details()
        token_id = encrypt(full_flair)
        details = {}
        details.update(anime_details)
        # Playback is resolved lazily via /streaming/video (same as the player source URL).
        details["video_link"] = f"/streaming/video?id={token_id}"
        details["full_title"] = series.get_title()
        details["partial_flair"] = f"/watch/{title_flair}/episode-"
        details["flair"] = title_flair
        details["cover"] = anime_details["cover"]
        details["episode_now"] = episode
        details["episode_next"] = (
            episode_next.replace(".", "-") if episode_next else None
        )
        details["episode_prev"] = (
            episode_prev.replace(".", "-") if episode_prev else None
        )
        details["_episode_flair"] = full_flair
        details["stream_provider"] = Constants.provider
        details["playback_json_url"] = f"/streaming/playback.json?id={token_id}"
        return details

    def _master_url_for_flair(self, episode_flair: str) -> str:
        token_id = encrypt(episode_flair)
        return f"/streaming/video?id={token_id}"

    def _playback_json_url_for_flair(self, episode_flair: str) -> str:
        token_id = encrypt(episode_flair)
        return f"/streaming/playback.json?id={token_id}"

    def _proxied_subtitle_url(self, upstream_url: str) -> str:
        token = encrypt(
            upstream_url,
            differentiator="subtitle_proxy",
            valuator=0,
            xor_mode=True,
        )
        return f"/streaming/subtitle/{token}"

    def _active_audio_id(self, episode_flair: str) -> str:
        parts = episode_flair.split(":")
        if len(parts) >= 4 and parts[0] == "anilist":
            audio = parts[3]
            if audio in ("sub", "dub"):
                return audio
        return "default"

    def playback_descriptor(self, episode_flair: str) -> dict | None:
        """Captions-only payload; stream master and in-manifest audio come from /streaming/video."""
        try:
            video_data = self.sources_for_episode_flair(episode_flair)
        except frzw_exceptions.VideoNotFound:
            return None

        media = {"subtitles": [], "audio": []}
        resp = hls_hosting.fetch_upstream(video_data.video_url)
        if resp and resp.text:
            media = parse_hls_master_media(resp.text)

        subtitle_tracks = [
            {
                "id": row.get("group_id") or row.get("language") or row.get("name") or "subs",
                "label": row.get("name") or row.get("language") or "Subtitles",
                "language": row.get("language") or "",
                "source": "hls",
                "kind": "vtt",
                "hlsGroupId": row.get("group_id") or "",
            }
            for row in media.get("subtitles") or []
        ]

        player = self.player_for_episode_flair(episode_flair)
        for row in external_subtitles_for_player(player):
            track_id = f"{row.get('lang', '')}-{row.get('label', '')}".strip("-") or "sub"
            upstream = row.get("url") or ""
            if not upstream:
                continue
            subtitle_tracks.append(
                {
                    "id": track_id,
                    "label": row.get("label") or row.get("lang") or "Subtitles",
                    "language": row.get("lang") or "",
                    "source": "external",
                    "kind": (row.get("kind") or "vtt").lower(),
                    "url": self._proxied_subtitle_url(upstream),
                }
            )

        return {
            "subtitles": subtitle_tracks,
            "defaults": {
                "captions": "off",
            },
        }

    def playback_descriptor_for_watch(self, title_flair: str, episode: str) -> dict | None:
        flair = self.episode_flair(title_flair, episode)
        if not flair:
            return None
        return self.playback_descriptor(flair)


streaming = Streaming(catalog)
