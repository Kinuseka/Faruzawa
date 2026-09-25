from flask import Blueprint, render_template, request as Request, Response, abort
from bridge import streaming
from bridge import hls_hosting
from essentials.tools import decrypt
import frzw_exceptions
from loguru import logger

log = logger.bind(name="CFSession")

video_handler = Blueprint('video_handler', __name__)

_M3U8 = 'application/vnd.apple.mpegurl'


@video_handler.route("/streaming/video")
def m3u8proxy():
    id = Request.args.get('id')
    if not id:
        return abort(404)
    data = decrypt(id)
    if not data:
        return render_template('errortemplates/serverError.html.j2', ajax=True), 500
    try:
        video_data = streaming.sources_for_episode_flair(data)
    except frzw_exceptions.VideoNotFound as e:
        log.warning(f"stream resolve failed for episode token: {e.message[:200]}")
        return abort(404)
    resp = hls_hosting.fetch_upstream(video_data.video_url)
    if not resp:
        return render_template('errortemplates/serverError.html.j2', ajax=True), 500
    body = hls_hosting.rewrite_master_playlist(resp.text, video_data.video_url)
    return Response(body, mimetype=_M3U8)


@video_handler.route("/streaming/hls/<id>")
def proxym3u8(id):
    data = decrypt(id, differentiator="m3u8_proxy", valuator=0, xor_mode=True)
    if not data:
        data = decrypt(id, differentiator="m3u8_proxy")
    log.debug(f'[proxym3u8] {data}')
    if not data:
        return render_template('errortemplates/serverError.html.j2', ajax=True), 500
    resp = hls_hosting.fetch_upstream(data)
    if not resp:
        return render_template('errortemplates/serverError.html.j2', ajax=True), 500
    if not resp.content.lstrip().startswith(b"#EXT"):
        body, mimetype = hls_hosting.segment_response(resp)
        return Response(
            body,
            mimetype=mimetype,
            headers={'X-Content-Type-Options': 'nosniff', 'Accept-Ranges': 'bytes'},
        )
    content = hls_hosting.rewrite_media_playlist(resp.text, data)
    return Response(content, mimetype=_M3U8)


@video_handler.route("/streaming/hls/key")
def proxy_hls_key():
    token = Request.args.get("id")
    if not token:
        return abort(404)
    data = decrypt(token, differentiator="hls_key_proxy", valuator=0, xor_mode=True)
    if not data:
        data = decrypt(token, differentiator="hls_key_proxy")
    log.debug(f'[proxy_hls_key] {data}')
    if not data:
        return render_template('errortemplates/serverError.html.j2', ajax=True), 500
    resp = hls_hosting.fetch_upstream(data, strict_mode=True)
    if not resp:
        return render_template('errortemplates/serverError.html.j2', ajax=True), 500
    mimetype = (resp.headers.get("Content-Type") or "application/octet-stream").split(";")[0]
    return Response(
        resp.content or b"",
        mimetype=mimetype,
        headers={'X-Content-Type-Options': 'nosniff', 'Accept-Ranges': 'bytes'},
    )


@video_handler.route("/streaming/hls/media/<id>")
def streamm3u8(id):
    seg_index = Request.args.get("v", type=int)
    if seg_index is None:
        return abort(404)
    data = decrypt(
        id,
        differentiator="streamer",
        valuator=seg_index,
        xor_mode=True,
    )
    log.debug(f'[streamm3u8] {data}')
    if not data:
        return render_template('errortemplates/serverError.html.j2', ajax=True), 500
    resp = hls_hosting.fetch_upstream(data, strict_mode=True)
    if not resp:
        return render_template('errortemplates/serverError.html.j2', ajax=True), 500
    body, mimetype = hls_hosting.segment_response(resp)
    return Response(
        body,
        mimetype=mimetype,
        headers={'X-Content-Type-Options': 'nosniff', 'Accept-Ranges': 'bytes'},
    )
