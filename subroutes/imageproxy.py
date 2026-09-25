from flask import Blueprint, Response

from API import image_cdn_base, primary_image_cdn
from essentials.cache_session import ImageSession
import requests.exceptions

# from requests import Session as rSession
# from cachetools import cached, LRUCache, TTLCache
img_proxy = Blueprint('image_proxy', __name__)
external_image_proxy = Blueprint('external_image_proxy', __name__)

session = ImageSession


def _fetch_image_stream(build: str):
    return session.get(build, stream=True, timeout=15)


# @cached(cache=TTLCache(maxsize=64, ttl=300))
def fetch_image_cover(path: str):
    build = f'{primary_image_cdn().rstrip("/")}/{path}'
    return _fetch_image_stream(build)


def fetch_external_image(path: str):
    base = image_cdn_base().rstrip("/")
    rel = path.lstrip("/")
    build = f"{base}/{rel}"
    return _fetch_image_stream(build)


def _image_response(response_obj, log_label: str = "imageproxy"):
    if response_obj.status_code == 200:

        def stream_chunks():
            try:
                for chunk in response_obj.iter_content(chunk_size=4096):
                    if chunk:
                        yield chunk
            except requests.exceptions.RequestException as e:
                print(f"[{log_label}] Image error down: {e}")
            finally:
                response_obj.close()

        headers = {
            k: v
            for k, v in response_obj.headers.items()
            if k.lower()
            in ("content-type", "content-length", "cache-control", "etag", "last-modified")
        }
        res = Response(
            stream_chunks(),
            status=response_obj.status_code,
            headers=headers,
        )
    elif response_obj.status_code == 404:
        response_obj.close()
        res = Response(response="Requested resource is not found", status=404)
    elif response_obj.status_code == 403:
        response_obj.close()
        res = Response(response="Forbidden", status=403)
    else:
        response_obj.close()
        res = Response(response="Backend error, contact support@kinuseka.us", status=500)
    return res


@img_proxy.route('/<path:param>')
def imageC(param):
    try:
        response_obj = fetch_image_cover(param)
    except requests.exceptions.RequestException as e:
        print(f"[imageproxy] Image fetch error: {e}")
        return Response("Backend error, contact support@kinuseka.us", status=502)
    return _image_response(response_obj)


@external_image_proxy.route('/<path:param>')
def image_ext(param):
    try:
        response_obj = fetch_external_image(param)
    except requests.exceptions.RequestException as e:
        print(f"[imgext] Image fetch error: {e}")
        return Response("Backend error, contact support@kinuseka.us", status=502)
    return _image_response(response_obj, log_label="imgext")
