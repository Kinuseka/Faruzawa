"""Playback resolution and watch-page context (provider-neutral facade)."""

from API import player_class
from API.registry import resolve
from bridge.catalog import catalog
from essentials.tools import encrypt
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
        return details


streaming = Streaming(catalog)
