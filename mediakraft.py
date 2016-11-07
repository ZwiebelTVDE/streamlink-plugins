#!/usr/bin/env python
# -*- coding: utf-8 -*-
import re
from streamlink.plugin import Plugin
from streamlink.plugin.api import http, validate
from streamlink.stream import HDSStream

CID=214637772664850569
CLIENT=619
AUTH_KEY="42B44B1E"
PLAY_MODE="single"
METHOD="videosforplayer"
SWF_URL = "http://nx-o.azureedge.net/swf/nexxPLAY_AZURE.swf?sv=553"
PROXY_URL="http://api.nexxcdn.com/proxy.php?cid={cid}&client={client}&authkey={authkey}&vid={video_id}&playmode={playmode}&method={method}"
STREAM_URL="{host}/{path}/{video_id}_src.ism/Manifest"
_url_re = re.compile(r"^(?:https?:\/\/)?(?:www.)?mediakraft\.tv\/videos\/(?P<video_id>[0-9]+)")

_playlist_schema = validate.Schema(
    {
        "locator" : validate.text,
        "azurehost" : validate.url(scheme=validate.any("http"))
    }
)
class Mediakraft(Plugin):

    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url)
        
    def _get_streams(self):
        url_match = _url_re.match(self.url)
        if url_match:
            video_id = url_match.group("video_id")
            proxy_url = PROXY_URL.format(video_id=video_id,cid=CID,playmode=PLAY_MODE,client=CLIENT,authkey=AUTH_KEY,method=METHOD)
            res = http.get(proxy_url)
            try:
                data = http.json(res, schema=_playlist_schema)
                stream_url = STREAM_URL.format(video_id=video_id,host=data['azurehost'],path=data['locator'])
                self.logger.debug(stream_url)
                return HDSStream.parse_manifest(self.session, stream_url,pvswf=SWF_URL)
            except Exception as ex:
                self.logger.debug(ex.message)
                return None
            return None
            
            
__plugin__ = Mediakraft