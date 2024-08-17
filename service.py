# -*- coding: utf-8 -*-


from urllib.parse import unquote

from yt_dlp import YoutubeDL

from iapc import public, Client, Service
from iapc.tools import notify, ICONERROR


# ------------------------------------------------------------------------------
# YtDlpInfo

class YtDlpInfo(dict):

    def __init__(self, info):
        super(YtDlpInfo, self).__init__(
            url=info.get("manifest_url"),
            duration=info.get("duration", -1),
            title=info.get("fulltitle", ""),
            description=info.get("description") or "",
            thumbnail=info.get("thumbnail"),
            formats=info.get("formats", [])
        )


# ------------------------------------------------------------------------------
# YtDlpService

class YtDlpService(Service):

    def __init__(self, *args, **kwargs):
        super(YtDlpService, self).__init__(*args, **kwargs)
        self.__extractor__ = YoutubeDL()
        self.__manifests__ = Client("service.dash.manifest")

    def start(self, **kwargs):
        self.logger.info("starting...")
        self.serve(**kwargs)
        self.logger.info("stopped")

    def __raise__(self, error, throw=True):
        if not isinstance(error, Exception):
            error = Exception(error)
        notify(f"error: {error}", icon=ICONERROR)
        if throw:
            raise error

    def __extract__(self, url):
        try:
            return self.__extractor__.extract_info(unquote(url), download=False)
        except Exception as error:
            self.__raise__(error)


    def __video_stream__(self, fmt):
        return {
            "contentType": "video",
            "lang": None,
            "averageBitrate": int(fmt["vbr"] * 1000),
            "width": fmt["width"],
            "height": fmt["height"],
            "frameRate": fmt["fps"]
        }

    def __audio_stream__(self, fmt):
        return {
            "contentType": "audio",
            "lang": fmt["language"],
            "averageBitrate": int(fmt["abr"] * 1000),
            "audioSamplingRate": fmt["asr"],
            "audioChannels": fmt["audio_channels"]
        }

    def __streams__(self, formats):
        for fmt in formats:
            if (
                (fmt.get("container", "").endswith("_dash")) and
                (
                    (
                        (codec := fmt.get("vcodec")) and
                        (
                            (codec != "none") and
                            (fmt.get("acodec") == "none")
                        ) and
                        (stream := self.__video_stream__(fmt))
                    ) or
                    (
                        (codec := fmt.get("acodec")) and
                        (
                            (codec != "none") and
                            (fmt.get("vcodec") == "none")
                        ) and
                        (stream := self.__audio_stream__(fmt))
                    )
                )
            ):
                stream.update(
                    {
                        "mimeType": f"{stream['contentType']}/{fmt['ext']}",
                        "id": fmt["format_id"],
                        "codecs": codec,
                        "url": fmt["url"],
                        "indexRange": fmt["indexRange"],
                        "initRange": fmt["initRange"]
                    }
                )
                yield stream

    def __manifest__(self, duration, formats):
        if (streams := list(self.__streams__(formats))):
            return self.__manifests__.manifest(duration, streams)

    # public api ---------------------------------------------------------------

    #@public
    #def play(self, url):
    #    if (info := YtDlpInfo(self.__extract__(url))):
    #        formats = info.pop("formats")
    #        if info["url"]:
    #            manifestType, mimeType = ("hls", "application/x-mpegURL")
    #        else:
    #            info["url"] = self.__manifest__(info["duration"], formats)
    #            manifestType, mimeType = ("mpd", "application/dash+xml")
    #    return (info, manifestType, {"mimeType": mimeType})

    @public
    def play(self, url):
        if (info := YtDlpInfo(self.__extract__(url))):
            formats = info.pop("formats")
            if info["url"]:
                manifestType = "hls"
            else:
                info["url"] = self.__manifest__(info["duration"], formats)
                manifestType = "mpd"
        return (info, manifestType, {})


# __main__ ---------------------------------------------------------------------

if __name__ == "__main__":
    YtDlpService().start()
