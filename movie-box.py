#!/usr/bin/env python
import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http, validate
from streamlink.stream import HTTPStream

VIDEO_URL="http://movie-box.pl/video/{id}.mp4"
_url_re = re.compile(r"http://(?:www.)?movie-box.pl/(?P<video_id>\d+)/(.+)")

class MovieBox(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url)

    def _get_streams(self):
        url_match = _url_re.match(self.url)
        if url_match:
            video_id = url_match.group("video_id")
            video_url = VIDEO_URL.format(id=video_id)
            stream = HTTPStream(self.session, video_url)

            return {'video' : stream }


__plugin__ = MovieBox

