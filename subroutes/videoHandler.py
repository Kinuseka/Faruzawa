from flask import Blueprint, jsonify, render_template, request as Request, Response, abort
from urllib.parse import urlparse
from bridge import streaming
from bridge import hls_hosting
from API.SubtitleConvert import srt_to_vtt
from essentials.tools import decrypt
import frzw_exceptions
from loguru import logger

log = logger.bind(name="CFSession")

video_handler = Blueprint('video_handler', __name__)

_M3U8 = 'application/vnd.apple.mpegurl'
_SEGMENT_HEADERS = {'X-Content-Type-Options': 'nosniff', 'Accept-Ranges': 'bytes'}


def _streaming_segment_response(upstream_resp, chunk_iter, *, prefix: bytes = b""):
    from API.HlsProxy import segment_body_mimetype

    mimetype = segment_body_mimetype(upstream_resp, prefix or None)
    return Response(chunk_iter, mimetype=mimetype, headers=_SEGMENT_HEADERS)


@video_handler.route("/streaming/subtitle/<id>")
def proxy_subtitle(id):
    token = id
    upstream_url = decrypt(
        token, differentiator="subtitle_proxy", valuator=0, xor_mode=True
    )
    if not upstream_url:
        upstream_url = decrypt(token, differentiator="subtitle_proxy")
    if not upstream_url:
        return abort(404)
    resp = hls_hosting.fetch_upstream(upstream_url, strict_mode=True)
    if not resp:
        return abort(404)
    body = resp.content or b""
    path = urlparse(upstream_url).path.lower()
    want_vtt = Request.args.get("format") == "vtt"
    if want_vtt or path.endswith(".srt"):
        try:
            text = body.decode("utf-8", errors="replace")
        except AttributeError:
            text = str(body)
        body = srt_to_vtt(text).encode("utf-8")
        mimetype = "text/vtt; charset=utf-8"
    elif path.endswith(".vtt") or body[:6].upper() == b"WEBVTT":
        mimetype = "text/vtt; charset=utf-8"
    elif path.endswith((".ass", ".ssa")):
        mimetype = "text/plain; charset=utf-8"
    else:
        mimetype = (resp.headers.get("Content-Type") or "text/plain").split(";")[0]
    return Response(
        body,
        mimetype=mimetype,
        headers={"X-Content-Type-Options": "nosniff", "Accept-Ranges": "bytes"},
    )


@video_handler.route("/streaming/playback.json")
def playback_json():
    token = Request.args.get("id")
    if not token:
        return abort(404)
    episode_flair = decrypt(token)
    if not episode_flair:
        return abort(404)
    descriptor = streaming.playback_descriptor(episode_flair)
    if not descriptor:
        return abort(404)
    return jsonify(descriptor)


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
    resp = hls_hosting.open_upstream_segment_stream(data)
    if not resp:
        return render_template('errortemplates/serverError.html.j2', ajax=True), 500
    prefix, body_iter = hls_hosting.read_stream_head(resp)
    if prefix.lstrip().startswith(b"#EXT"):
        text = hls_hosting.playlist_text_from_stream(body_iter)
        content = hls_hosting.rewrite_media_playlist(text, data)
        return Response(content, mimetype=_M3U8)
    return _streaming_segment_response(resp, body_iter, prefix=prefix)


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
    resp = hls_hosting.open_upstream_segment_stream(data, strict_mode=True)
    if not resp:
        return render_template('errortemplates/serverError.html.j2', ajax=True), 500
    _prefix, chunk_iter = hls_hosting.read_stream_head(resp, max_bytes=0)
    return _streaming_segment_response(resp, chunk_iter)
