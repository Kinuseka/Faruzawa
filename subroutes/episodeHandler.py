from flask import Blueprint, render_template
from flask import abort, request as f_request
from bridge import catalog, streaming
from essentials.essentials import sitemap
import frzw_exceptions
from loguru import logger

log = logger.bind(name="CFSession")
episode_handler = Blueprint('episode_handler', __name__)

def sitemap_generator(type_data):
    def _generator():
        return catalog.sitemap_entries(type_data)
    return _generator

@sitemap.include(priority=0.7,changefreq="daily",url_variables=sitemap_generator('popular'))
@episode_handler.route('/watch/<title>', methods=['GET'])
def episodeIndex(title):
    details = catalog.prewatch(title)
    if not details:
        return abort(404)
    return render_template('prewatch.html.j2', details=details)

@sitemap.include(priority=0.7,changefreq="daily",url_variables=sitemap_generator('new'))
@episode_handler.route('/watch/<title>/episode-<episode>', defaults={'de_episode': None}, methods=['GET'])
@episode_handler.route('/watch/<title>/episode-<episode>-<de_episode>', methods=['GET'])
def watchPage(title,episode,de_episode):
    if not episode: return abort(404)
    try:
        if de_episode:
            episode = episode +'.'+de_episode
        else:
            episode = episode
    except ValueError: # Do not change, Error when user passes non int value
        return abort(404)
    try:
        details = streaming.watch_context(title, episode)
    except frzw_exceptions.VideoNotFound as e:
        log.warning(f"watchPage stream/catalog miss {title} ep {episode}: {e.message}")
        return abort(404)
    if not details:
        log.warning(f"watchPage no context for {title} episode {episode}")
        return abort(404)
    full_flair = details.pop("_episode_flair", None)
    log.info(f'[{f_request.remote_addr}] View: {f_request.base_url} as {full_flair}')
    return render_template('watchvideo.html.j2', details=details)
