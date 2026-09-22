from essentials.cache_session import VideoHandlerSession
import requests.exceptions
import frzw_exceptions
from bs4 import BeautifulSoup
from urllib import parse
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from collections import UserDict
from constants import Constants
import base64
import json
import m3u8
import re

class RequestsClient():
    def download(self, uri, timeout=None, headers={}, verify_ssl=True):
        session = VideoHandlerSession
        o = session.get(uri, timeout=timeout, headers=headers)
        return o.text, o.url

class VideoData(UserDict):
    def __init__(self, data):
        self.video_url = data['source'][0]['file']
        self.m3u8_data = m3u8.load(self.video_url, http_client=RequestsClient())
        final_data = self.sort_data(self.video_url)
        self.data = final_data
    
    def sort_data(self, url, full_url = True):
        final_data = {
            'source': []
        }
        parsed_url = self._parse_url(url)
        for each in self.m3u8_data.playlists:
            template = {
                'url': None,
                'quality': None,
                'isM3U8': True
            }
            resolution = each.stream_info.resolution[1]
            template['quality'] = f'{resolution}'
            reparse = parsed_url.path.split("/")[:-1]
            reparse.append(each.uri)
            if full_url:
                template['url'] = f'{parsed_url.scheme}://{parsed_url.hostname}{"/".join(reparse)}'
            else:
                template['url'] = f'{"/".join(reparse)}'
            final_data['source'].append(template)
        return final_data
    def _parse_url(self, url):
        return parse.urlparse(url)         

    def get_sources(self):
        return self.data['source']

class GogoCDN:
    def __init__(self, flair):
        self.url = f"{Constants.gogoanime}/{flair}"
        self.session = VideoHandlerSession
        try:
            self.parsed = self.fetch_site_data(self.url)
        except requests.exceptions.RequestException:
            raise frzw_exceptions.VideoNotFound("Not Found")
        self.keys = {
            'key': b'37911490979715163134003223491201',
            'secondKey': b'54674138327930866480207815084989',
            'iv': b'3134003223491201'
        }

    def fetch_site_data(self, url):
        res = self.session.get(url)
        res.raise_for_status()
        return BeautifulSoup(res.content, "html.parser")
    
    def encrypt(self, plain_text):
        cipher = AES.new(self.keys['key'], AES.MODE_CBC, self.keys['iv'])
        ciphertext = cipher.encrypt(pad(plain_text.encode('utf-8'), AES.block_size))
        return base64.b64encode(ciphertext).decode('utf-8')

    def decrypt(self, encrypted_text, second=False):
        encrypted_text = base64.b64decode(encrypted_text)
        cipher = AES.new(self.keys['secondKey'] if second else self.keys['key'], AES.MODE_CBC, self.keys['iv'])
        decrypted_text = unpad(cipher.decrypt(encrypted_text), AES.block_size)
        return decrypted_text.decode('utf-8')

    def get_streaming_url(self):
        """Get the embed url of the video stream"""
        container_anime = self.parsed.find("div", class_="anime_muti_link")
        streaming_url = container_anime.find("a", class_="active")["data-video"]
        return streaming_url
    
    def get_streaming_value(self):
        """Encrypted streaming data"""
        parsed = self.fetch_site_data(self.get_streaming_url())
        streaming_container = parsed.find('script', {'data-name': 'episode'})['data-value']
        return streaming_container

    def get_streaming_data(self):
        """Get the available video data for the video stream"""
        payload = self.extract_data()
        url_parse = self._parse_url(self.get_streaming_url())
        url_full = f'{url_parse.scheme}://{url_parse.hostname}/encrypt-ajax.php?id={payload["id"]}&alias={payload["alias"]}&token={payload["token"]}'
        res = self.session.get(url_full, headers={'X-Requested-With': 'XMLHttpRequest'})
        data = res.json()['data']
        decrypted_data = self.decrypt(data, second=True)
        return VideoData(json.loads(decrypted_data))

    
    def get_referrer(self):
        return {'Referer': self.get_streaming_url()}
    
    def _parse_url(self, url):
        return parse.urlparse(url)

    def _parse_query(self, parsedurl: parse.ParseResult):
        return parse.parse_qs(parsedurl.query)

    def extract_data(self, url=None):
        if not url:
            url = self.get_streaming_url()
        id = self._parse_query(self._parse_url(url))['id'][0]
        id_encoded = self.encrypt(id)
        token_value = self.decrypt(self.get_streaming_value())
        return {
            'id': id_encoded,
            'alias': id,
            'token': token_value
        }    