import re
import socket
import struct
import os
import random
from streamlink.plugin import Plugin
from streamlink.plugin.api import http, validate, utils
from streamlink.stream import RTMPStream
from streamlink.logger import LoggerModule

SWF_URL = "https://showup.tv/flash/SmallBug.swf"
RANDOM_UID = '%032x' % random.getrandbits(128)
JSON_UID = u'{"id":0,"value":["%s",""]}'
JSON_CHANNEL = u'{"id":2,"value":["%s"]}'

_url_re = re.compile(r"http(s)?://(\w+.)?showup.tv/(?P<channel>[A-Za-z0-9_-]+)")
_websocket_url_re = re.compile(r"startChildBug\(.*'(?P<ws>[\w.]+:\d+)'\);")
_rtmp_url_re = re.compile(r'\{"id":\d+,"value":\["joined","(?P<rtmp>.+\.showup\.tv)"\]\}')
_channel_id_re = re.compile(r'\{"id":\d+,"value":\["(?P<id>\w+)"\]\}')

class SimpleWebSocketClient():
    def __init__ (self):
        self.socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        
    def close(self):          
        self.socket.close()
        
    def send(self, data, final=True):
        head = 0
        if final:
            head |= 0x8000
        head |= 1 << 8
        ld = len (data)
        if ld >= 126:
            return
        head |= ld
        p = [ struct.pack ('!H', head), bytes(data.encode()) ]
        self.socket.send(b''.join(p))
            
    def recv(self, size):
        return (self.socket.recv(size)[2:]).decode('utf-8','ignore')

        
    def _handshake(self):
        headers = []
        headers.append("GET / HTTP/1.1")
        headers.append("Upgrade: websocket")
        headers.append("Sec-WebSocket-Key: x3JJHMbDL1EzLkh9GBhXDw==")
        headers.append("Sec-WebSocket-Version: 13")
        headers.append("Origin: http://%s" % self.host)
        headers.append("Host: %s" % self.host)
        header = "\r\n".join(headers)
        header += "\r\n\r\n"
        self.socket.send(bytes(header.encode()))
        result = self.socket.recv(1024).decode()
        return "Switching Protocols" in result
       
    def connect(self,websocket_url):
        if 'ws://' not in websocket_url:
            return False
        websocket_url = websocket_url[5:]  
        splited = websocket_url.split(':')
        self.host = splited[0]
        try:
            self.port = int(splited[1])
        except:
            self.port = 80
        self.socket.connect((self.host,self.port))
        return self._handshake()   


class ShowUp(Plugin):
    @classmethod
    def can_handle_url(self, url):
        return _url_re.match(url)
    
    def _get_stream_id(self, data):
        channel_id = _channel_id_re.search(data)
        if channel_id:
            return channel_id.group('id')

    def _get_websocket_data(self,channel, websocket):
        ws = SimpleWebSocketClient()
        if not ws.connect(websocket):
            return None
        ws.send(JSON_UID % RANDOM_UID)
        ws.send(JSON_CHANNEL % channel)
        data = ws.recv(64)+ws.recv(64)
        ws.close()
        return data
        
    def _get_websocket(self,html):
        websocket = _websocket_url_re.search(html)
        if websocket:
            return "ws://%s" % websocket.group("ws")
            
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
        self.logger.debug(u'Channel name: %s' % channel)
        self.logger.debug(u'WebSocket: %s' % websocket)
        self.logger.debug(u'Stream ID: %s' % stream_id)
        self.logger.debug(u'RTMP Url: %s' % "{0}/{1}".format(rtmp, stream_id))
        if rtmp is None:
            return None
        stream = RTMPStream(self.session, {
            "rtmp": "{0}/{1}".format(rtmp, stream_id),
            "pageUrl": self.url,
            "swfVfy": SWF_URL,
            "live": True
        })
        return {'live' : stream}

__plugin__ = ShowUp
