#!/usr/bin/env python
import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http, validate
from streamlink.stream import HTTPStream

_url_re = re.compile(r"http://(?:www.)?motherless.com/.*")
_video_re = re.compile(r"__fileurl = '(?P<video_url>[^']+)'")

class Motherless(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url)

    def _get_streams(self):
        page = http.get(self.url)
        video_match = _video_re.search(page.text)
        if video_match:
            video_url = video_match.group("video_url")
            stream = HTTPStream(self.session, video_url)

            return {'video' : stream }


__plugin__ = Motherless

