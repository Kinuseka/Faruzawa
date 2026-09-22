from flask import Blueprint, Response
from constants import Constants
from essentials.cache_session import ImageSession
import requests.exceptions

# from requests import Session as rSession
# from cachetools import cached, LRUCache, TTLCache
img_proxy = Blueprint('image_proxy', __name__)

session = ImageSession

# @cached(cache=TTLCache(maxsize=64, ttl=300))
def fetch_image_cover(path: str):
    build = f'{Constants.gogocdn}/{path}'
    image = session.get(build, stream=True, timeout=15)
    if image.status_code != 200:
        return None, image
    max_size = image.headers.get("content-length")
    tries = 5
    content = b''
    for attempt in range(1, tries+1):
        content = b''
        try:
            for chunk in image.iter_content(chunk_size=4096):
                content += chunk
            else:
                if len(content) != int(max_size):
                    print(f"[imageproxy] Warn! collected content does not match max_size ({len(content)}/{max_size})")
                break
        except requests.exceptions.RequestException as e:
            print(f"[imageproxy] Image error down: {e}, ({attempt}/{tries})")
    else:
        print(f"[imageproxy] Attempts reached max, ({len(content)}/{max_size})")
    return content, image

@img_proxy.route('/<path:param>')
def imageC(param):
    data, response_obj = fetch_image_cover(param)
    if response_obj.status_code == 200:
        res = Response(response=data, status=response_obj.status_code, headers=response_obj.headers.items())
    elif response_obj.status_code == 404:
        res = Response(response="Requested resource is not found", status=404)
    elif response_obj.status_code == 403:
        res = Response(response="Forbidden", status=403)
    else:
        res = Response(response="Backend error, contact support@kinuseka.us", status=500)
    return res
