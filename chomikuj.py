#!/usr/bin/env python
import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http, validate
from streamlink.stream import HTTPStream

AUDIO_URL="http://chomikuj.pl/Audio.ashx?type=2&tp=mp3&id={id}"
_url_re = re.compile(r"http://(?:www.)?chomikuj.pl/(.+),(?P<audio_id>\d+)\.mp3")

class Chomikuj(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url)

    def _get_streams(self):
        url_match = _url_re.match(self.url)
        if url_match:
            audio_id = url_match.group("audio_id")
            audio_url = AUDIO_URL.format(id=audio_id)
            stream = HTTPStream(self.session, audio_url)

            return {'audio' : stream }


__plugin__ = Chomikuj

