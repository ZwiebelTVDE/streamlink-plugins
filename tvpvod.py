#!/usr/bin/env python
# -*- coding: utf-8 -*-
import re
from streamlink.compat import urlparse
from streamlink.plugin import Plugin
from streamlink.plugin.api import StreamMapper, http, validate
from streamlink.stream import HTTPStream, HLSStream

PLAYLIST_URL="http://www.tvp.pl/shared/cdn/tokenizer_v2.php?object_id={video_id}"
_url_re = re.compile(r"https?:\/\/(?:www.)?vod\.tvp\.pl/(?P<video_id>[0-9]+)")
_playlist_schema = validate.Schema(validate.get('formats'))

class TvpVod(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url)

    def _get_quality(self,bitrate):
        if bitrate <= 590000:
            return '224p'
        elif bitrate <= 820000:
            return '270p'
        elif bitrate <= 1250000:
            return '360p'
        elif bitrate <= 1750000:
            return '450p'
        elif bitrate <= 2850000:
            return '540p'
        elif bitrate <= 5420000:
            return '720p'
        else:
            return '1080p'
            
    def _create_http_streams(self,video):
        video_url = video["url"]
        quality = self._get_quality(video["totalBitrate"])
        stream =  HTTPStream(self.session, video_url)
        yield quality, stream
                
    def _create_hls_streams(self,video):
        streams = HLSStream.parse_variant_playlist(self.session, video["url"])
        for stream in streams.items():
            yield stream

    def _get_streams(self):
        url_match = _url_re.match(self.url)
        if url_match:
            video_id = url_match.group("video_id")
            res = http.get(PLAYLIST_URL.format(video_id=video_id))
            try:
                data = http.json(res, schema=_playlist_schema)
            except Exception:
                return None
            mapper = StreamMapper(cmp=lambda mimetype, video: video["mimeType"] == mimetype)
            mapper.map("video/mp4", self._create_http_streams)
            mapper.map("application/x-mpegurl", self._create_hls_streams)
            return mapper(data)

__plugin__ = TvpVod

