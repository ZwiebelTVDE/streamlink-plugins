#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import re
import base64
import binascii
import time

from hashlib import sha1
from Crypto.Cipher import AES
from streamlink.plugin import Plugin
from streamlink.plugin.api import http, validate
from streamlink.stream import HTTPStream

platforms = [
    {
        'platform': 'ConnectedTV',
        'terminal': 'Panasonic',
        'authKey': '064fda5ab26dc1dd936f5c6e84b7d3c2',
        'apiVer': '3.1',
        'encrypt': False
    }, {
        'platform': 'Mobile',
        'terminal': 'Android',
        'authKey': 'b4bc971840de63d105b3166403aa1bea',
        'apiVer': '3.0',
        'encrypt': True
    }
]

USER_AGENT = 'Mozilla/5.0'

PLAYLIST_URL = "http://player.pl/api/?id={video_id}&platform={platform}&terminal={terminal}&format=json&v={api}&authKey={authkey}&type=episode&&m=getItem"
_url_re = re.compile(r"^(?:https?:\/\/)?(?:www.)?player\.pl/[^\"]+,(?P<video_id>[0-9]+).html.*")
_playlist_schema = validate.Schema(
    {
        "item": {
            "videos": {
                "main": {
                    "video_content": validate.all([
                        {
                            "profile_name": validate.text,
                            "url": validate.url(scheme=validate.any("http"))
                        }
                    ])
                }
            }
        }
    },
    validate.get("item"),
    validate.get("videos"),
    validate.get("main"),
    validate.get("video_content")
)
QUALITY_MAP = {
    u"Standard": "720p",
    u"HD": "1080p",
    u"SD": "640p",
    u"Bardzo wysoka": "1080p",
    u"Średnia": "720p",
    u"Wysoka": "640p",
    u"Niska": "512p",
    u"Bardzo niska": "320p",
}


class TvnPlayer(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url)

    def _get_salt_and_token(self, url):
        url = url.replace('http://redir.atmcdn.pl/http/', '')
        SecretKey = 'AB9843DSAIUDHW87Y3874Q903409QEWA'
        iv = 'ab5ef983454a21bd'
        KeyStr = '0f12f35aa0c542e45926c43a39ee2a7b38ec2f26975c00a30e1292f7e137e120e5ae9d1cfe10dd682834e3754efc1733'
        salt = sha1()
        salt.update(os.urandom(16))
        salt = salt.hexdigest()[:32]

        tvncrypt = AES.new(SecretKey, AES.MODE_CBC, iv)
        key = tvncrypt.decrypt(binascii.unhexlify(KeyStr))[:32]

        expire = 3600000 + long(time.time() * 1000) - 946684800000

        unencryptedToken = "name=%s&expire=%s\0" % (url, expire)

        pkcs5_pad = lambda s: s + (16 - len(s) % 16) * chr(16 - len(s) % 16)
        pkcs5_unpad = lambda s: s[0:-ord(s[-1])]

        unencryptedToken = pkcs5_pad(unencryptedToken)

        tvncrypt = AES.new(binascii.unhexlify(key), AES.MODE_CBC, binascii.unhexlify(salt))
        encryptedToken = tvncrypt.encrypt(unencryptedToken)
        encryptedTokenHEX = binascii.hexlify(encryptedToken).upper()

        return salt, encryptedTokenHEX

    def _get_all_streams(self, video_content, encrypt):
        for video in video_content:
            url = video["url"]
            quality = QUALITY_MAP[video["profile_name"]]
            if encrypt:
                salt, token = self._get_salt_and_token(url)
                video_url = url + '?salt=%s&token=%s' % (salt, token)
            else:
                video_url = url
            stream = HTTPStream(self.session, video_url)
            yield quality, stream

    def _check_platform(self, video_id, platform):
        playlist = PLAYLIST_URL.format(video_id=video_id,
                                       terminal=platform['terminal'],
                                       platform=platform['platform'],
                                       api=platform['apiVer'],
                                       authkey=platform['authKey'])
        self.logger.debug("PLAYLIST URL: " + playlist)
        res = http.get(playlist)
        try:
            data = http.json(res, schema=_playlist_schema)
        except Exception as ex:
            self.logger.debug(ex.message)
            return None
        return self._get_all_streams(data, platform['encrypt'])

    def _get_streams(self):
        url_match = _url_re.match(self.url)
        if url_match:
            http.headers.update({"User-Agent": USER_AGENT})
            video_id = url_match.group("video_id")
            for platform in platforms:
                streams = self._check_platform(video_id, platform)
                if streams:
                    return streams

            return None


__plugin__ = TvnPlayer
