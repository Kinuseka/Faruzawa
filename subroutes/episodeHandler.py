from flask import Blueprint, render_template, session
from flask import abort, request as f_request
from API import GogoAPI, GogoCDN
from essentials.tools import encrypt
from essentials.essentials import sitemap
import frzw_exceptions
from loguru import logger

log = logger.bind(name="CFSession")
episode_handler = Blueprint('episode_handler', __name__)

def fetch_gogo() -> GogoAPI:
    gogo = GogoAPI()
    return gogo

def sitemap_generator(type_data):
    def _generator():
        if type_data == "new":
            new = fetch_gogo().new().get_titles()
            return {"title": [result["raw_flair"] for result in new], 'episode': [result['episode'] for result in new]} 
        elif type_data == "popular":
            pop = fetch_gogo().popular().get_titles()
            return {"title": [result["raw_flair"] for result in pop]} 
    return _generator

@sitemap.include(priority=0.7,changefreq="daily",url_variables=sitemap_generator('popular'))
@episode_handler.route('/watch/<title>', methods=['GET'])
def episodeIndex(title):
    goapi = fetch_gogo()
    gogo = goapi.search_flair(title)
    if not gogo: return abort(404)
    details = gogo.get_anime_details()
    details['episode_keys'] = [list(each.keys())[0] for each in details.get('episode_meta')]
    details['episode_raw'] = [list(each.keys())[0].replace('.', '-') for each in details.get('episode_meta')]
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
    goapi = fetch_gogo()
    gogo = goapi.search_flair(title)
    if not gogo: return abort(404)
    full_flair = gogo.get_episode_link(episode)
    if full_flair:
        full_flair = full_flair[episode]['episode-flair']
    else:
        return abort(404)
    episode_next = gogo.get_episode_link(episode, adjustment=1)
    if episode_next:
        episode_next = list(episode_next.keys())[0]
    episode_prev = gogo.get_episode_link(episode, adjustment=-1)
    if episode_prev:
        episode_prev = list(episode_prev.keys())[0]
    log.info(f'[{f_request.remote_addr}] View: {f_request.base_url} as {full_flair}')
    try:
        GoVideo = GogoCDN(full_flair)
    except frzw_exceptions.VideoNotFound:
        return abort(404)
    details = {}
    max_episodes = gogo.get_episode_count()
    id = encrypt(full_flair)
    details.update(gogo.get_anime_details())
    details['streaming_data'] = GoVideo.get_streaming_data()['source']
    details['video_link'] = f"/streaming/video?id={id}"
    details['full_title'] = gogo.get_title()
    details['partial_flair'] = f"/watch/{title}/episode-"
    details['flair'] = title
    details['cover'] = gogo.get_anime_details()['cover']
    details['episode_now'] = episode
    details['episode_next'] = episode_next.replace('.', '-') if episode_next else None
    details['episode_prev'] = episode_prev.replace('.', '-') if episode_prev else None
    return render_template('watchvideo.html.j2', details=details)
