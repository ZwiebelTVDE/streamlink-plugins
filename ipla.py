#!/usr/bin/env python
# -*- coding: utf-8 -*-
import re
from streamlink.plugin import Plugin
from streamlink.plugin.api import http, validate
from streamlink.stream import HTTPStream

URL_SEARCH = u"http://getmedia.redefine.pl/vods/search/?vod_limit=50&page=0&keywords={keywords}"
USER_AGENT = "mipla/23"
_ipla_protocol_re = re.compile(r"ipla://[^|]+\|(?P<media_id>\w+)")
_ipla_title_re = re.compile(r'<meta content="(?P<title>.*)" property="ipla:title" />')
_url_re = re.compile(r"(?:https?:\/\/)?(?:www.)?ipla\.tv/.*")
_playlist_schema = validate.Schema(
    validate.xml_findall(".//vod"),
    [
        validate.union({
            "id": validate.all(         
                validate.xml_element(attrib={
                    "id": validate.text
                }),
                validate.get("id")),
            "videos": validate.all(
                validate.xml_findall("srcreq"),
                [
                    validate.all(
                        validate.xml_element(attrib={
                            "quality": validate.transform(int),
                            "url": validate.url(scheme=validate.any("http"))
                        }),
                        validate.transform(
                            lambda e: {"quality":e.attrib["quality"], "url":e.attrib["url"]}
                        )
                    )
                ]
            )
        })
    ]
)

QUALITY = {
            1:'360p',
            2:'576p',
            3:'720p'
          }

class IPLA(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url)
        
    def _get_all_streams(self,data, media_id):
        videos = (v["videos"] for v in data if v["id"] == media_id).next()
        for video in videos:
            video_url = video["url"]
            quality = QUALITY.get(video["quality"], '1080p')
            stream =  HTTPStream(self.session, video_url)
            yield quality, stream
                        
    def _get_streams(self):
        page = http.get(self.url)
        media_id_match = _ipla_protocol_re.search(page.text)
        title_match = _ipla_title_re.search(page.text)
        if media_id_match and title_match:
            title = title_match.group("title")    
            media_id = media_id_match.group("media_id")
            res = http.get(URL_SEARCH.format(keywords=title), headers = {'user-agent': USER_AGENT})
            try:
                data = http.xml(res, schema=_playlist_schema)
            except Exception:
                return None
            return self._get_all_streams(data,media_id)

__plugin__ = IPLA

