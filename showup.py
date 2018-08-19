import re
import socket
import struct
import os
import random
import websocket
import ssl
from streamlink.plugin import Plugin
from streamlink.plugin.api import http, validate, utils
from streamlink.stream import RTMPStream
from streamlink.logger import LoggerModule

RANDOM_UID = '%032x' % random.getrandbits(128)
JSON_UID = u'{"id":0,"value":["%s",""]}'
JSON_CHANNEL = u'{"id":2,"value":["%s"]}'
_url_re = re.compile(r"http(s)?://(\w+.)?showup.tv/(?P<channel>[A-Za-z0-9_-]+)")
_websocket_url_re = re.compile(r"socket.connect\('(?P<ws>[\w.]+):\d+'\);")
_rtmp_url_re = re.compile(r'\{"id":\d+,"value":\["joined","(?P<rtmp>.+\.showup\.tv)"\]\}')
_channel_id_re = re.compile(r'\{"id":\d+,"value":\["(?P<id>\w+)"\]\}')

class ShowUp(Plugin):
    @classmethod
    def can_handle_url(self, url):
        return _url_re.match(url)
    
    def _get_stream_id(self, data):
        channel_id = _channel_id_re.search(data)
        if channel_id:
            return channel_id.group('id')

    def _get_websocket_data(self,channel, websocket_url):
        ws = websocket.create_connection(websocket_url)
        if not ws:
            return None
        ws.send(JSON_UID % RANDOM_UID)
        ws.send(JSON_CHANNEL % channel)
        data = ws.recv()
        data += ws.recv()
        return data
        
    def _get_websocket(self,html):
        websocket = _websocket_url_re.search(html)
        if websocket:
            return "wss://%s" % websocket.group("ws")
            
    def _get_rtmp(self,data):
        rtmp = _rtmp_url_re.search(data)
        if rtmp:
            return "rtmp://{0}:1935/webrtc".format(rtmp.group("rtmp"))
        
    def _get_streams(self):
        url_match = _url_re.match(self.url)
        channel = url_match.group("channel")
        http.parse_headers('Referer: %s'%self.url)
        http.parse_cookies('accept_rules=true')
        page = http.get(self.url)
        websocket = self._get_websocket(page.text)
        data = self._get_websocket_data(channel, websocket)
        rtmp = self._get_rtmp(data)
        stream_id = self._get_stream_id(data)
        stream_id_suffix = "%s_aac" % stream_id
        self.logger.debug(u'Channel name: %s' % channel)
        self.logger.debug(u'WebSocket: %s' % websocket)
        self.logger.debug(u'Stream ID: %s' % stream_id)
        self.logger.debug(u'RTMP Url: %s' % "{0}/{1}".format(rtmp, stream_id_suffix))
        if rtmp is None:
            return None
        stream = RTMPStream(self.session, {
            "rtmp": "{0}/{1}".format(rtmp, stream_id_suffix),
            "live": True
        })
        return {'live' : stream}

__plugin__ = ShowUp
