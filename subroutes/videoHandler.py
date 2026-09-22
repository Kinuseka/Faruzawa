from flask import Blueprint, render_template, session, request as Request, Response
from essentials.cache_session import VideoHandlerSession
from essentials.tools import decrypt, encrypt
from urllib.parse import urlparse
from constants import Constants
from flask import abort
from API import GogoCDN
from loguru import logger
import requests.exceptions
log = logger.bind(name="CFSession")

video_handler = Blueprint('video_handler', __name__)
session = VideoHandlerSession

def proxify_video(url):
    try:
        resp = session.get(url, timeout=15)
        resp.raise_for_status()
        return resp
    except requests.exceptions.RequestException as e:
        log.exception('Failed to proxy on video_handler')
        return None
    except Exception as e:
        log.exception('Unknown on video_handler')
        return None

def convert_to_proxy(file_target, proxy_the):
    final = ""
    parsed_url = urlparse(proxy_the)
    i = 0
    for line in file_target.splitlines():
        if line.startswith("ep"):
            reparse = parsed_url.path.split("/")[:-1]
            reparse.append(line)
            line = f'{parsed_url.scheme}://{parsed_url.hostname}{"/".join(reparse)}'
            #Enable this line if you want to proxify videos
            # line = '/streaming/hls/media/'+encrypt(line, differentiator="streamer")
            #Enable this line to use the CDN proxy
            line = f"{Constants.videocdn}/video-streaming/hls/seg/"+encrypt(line, differentiator="streamer",valuator=i,xor_mode=True)+f"?v={i}"
            i += 1
        final += line + '\n'
    return final

@video_handler.route("/streaming/video")
def m3u8proxy():
    id = Request.args.get('id')
    if not id: return abort(404)
    data = decrypt(id)
    if not data: return render_template('errortemplates/serverError.html.j2', ajax=True), 500
    cdn = GogoCDN(data)
    video_data = cdn.get_streaming_data()
    parsed_url = video_data._parse_url(video_data.video_url)
    # print(video_data.sort_data('/streaming/hls/', full_url=False))
    resp = proxify_video(video_data.video_url)
    if not resp: return render_template('errortemplates/serverError.html.j2', ajax=True), 500
    final = ""
    for line in resp.text.splitlines():
        if line.startswith("ep"):
            reparse = parsed_url.path.split("/")[:-1]
            reparse.append(line)
            line = f'{parsed_url.scheme}://{parsed_url.hostname}{"/".join(reparse)}'
            line = '/streaming/hls/'+encrypt(line, differentiator="m3u8_proxy")
        final += line + '\n'
    return Response(final, mimetype='application/vnd.apple.mpegurl')

@video_handler.route("/streaming/hls/<id>")
def proxym3u8(id):
    data = decrypt(id, differentiator="m3u8_proxy")
    log.debug(f'[proxym3u8] {data}')
    if not data: return render_template('errortemplates/serverError.html.j2', ajax=True), 500
    resp = proxify_video(data)
    if not resp: return render_template('errortemplates/serverError.html.j2', ajax=True), 500
    content = convert_to_proxy(resp.text, data)
    return Response(content, mimetype='application/vnd.apple.mpegurl')

@video_handler.route("/streaming/hls/media/<id>")
def streamm3u8(id):
    data = decrypt(id, differentiator="streamer")
    log.debug(f'[streamm3u8] {data}')
    if not data: return render_template('errortemplates/serverError.html.j2', ajax=True), 500
    resp = proxify_video(data)
    if not resp: return render_template('errortemplates/serverError.html.j2', ajax=True), 500
    return Response(resp.content, mimetype='text/html')
    