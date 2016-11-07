#!/usr/bin/env python
# -*- coding: utf-8 -*-
import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http, validate, StreamMapper
from streamlink.stream import HTTPStream, HDSStream

PLAYLIST_URL="http://qi.ckm.onetapi.pl/?body[id]={video_id}&body[jsonrpc]=2.0&body[method]=get_asset_detail&body[params][ID_Publikacji]={video_id}&body[params][Service]=vod.onet.pl&content-type=application%2Fjsonp&x-onet-app=player.front.onetapi.pl&callback="
_url_re = re.compile(r"https?://(?:www.)?vod\.pl/.*")
_video_id_re = re.compile(r"mvp:(?P<video_id>[\d.]+)")
_playlist_schema = validate.Schema(
    {
        "result":{
                "0":{
                    "formats":{
                        "wideo":{
                            "mp4":validate.all([
                                {
                                    "video_bitrate_mode": validate.text,
                                    "vertical_resolution": validate.text,
                                    "url": validate.url(scheme=validate.any("http"))
                                }
                            ])
                        }
                    }
                }
        }
    },
    validate.get("result"),
    validate.get("0"),
    validate.get("formats"),
    validate.get("wideo"),
    validate.get("mp4")
)

class OnetVod(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url)
        
    def _create_http_stream(self,video):
        quality = "%sp"%video["vertical_resolution"]
        stream =  HTTPStream(self.session, video["url"])
        yield quality, stream

    def _get_streams(self):
        page = http.get(self.url)
        video_id_match = _video_id_re.search(page.text)
        if video_id_match:
            video_id = video_id_match.group("video_id")
            res = http.get(PLAYLIST_URL.format(video_id=video_id))
            try:
                data = http.json(res, schema=_playlist_schema)
            except Exception:
                return None
            mapper = StreamMapper(cmp=lambda bitrate_mode, video: video["video_bitrate_mode"] == bitrate_mode)
            mapper.map("constant", self._create_http_stream)
            return mapper(data)

__plugin__ = OnetVod

