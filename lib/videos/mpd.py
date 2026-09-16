# -*- coding: utf-8 -*-


from videos import defaultResolution, Codecs, FpsHints, NoneCodec


# ------------------------------------------------------------------------------

def __vdefault__(fmt, height, codec, vcodec):
    return (
        bool(height and defaultResolution(fmt, height)),
        bool(vcodec and codec.startswith(Codecs[vcodec]["names"]))
    )

def __video_stream__(
    fmt,
    inputstream="adaptive",
    fps_limit=0,
    fps_hint="int",
    height=None,
    vcodec=None,
    **kwargs
):
    codec = fmt["vcodec"]
    fps = fmt["fps"]
    if ((not fps_limit) or (fps <= fps_limit)):
        stream = {
            "codecs": codec,
            "bandwidth": int(fmt["vbr"] * 1000),
            "width": fmt["width"],
            "height": fmt["height"],
            "frameRate": FpsHints[fps_hint]["values"][fps]
        }
        if (inputstream == "adaptive"):
            if any(_default_ := __vdefault__(fmt, height, codec, vcodec)):
                stream["_default_"] = _default_
        return stream


def __adefault__(lang, track, codec, acodec):
    return (
        bool(track and lang.startswith(track)),
        bool(acodec and codec.startswith(Codecs[acodec]["names"]))
    )

def __audio_stream__(
    fmt,
    inputstream="adaptive",
    track=None,
    acodec=None,
    **kwargs
):
    codec = fmt["acodec"]
    lang = (fmt.get("language", "") or "")
    stream = {
        "codecs": codec,
        "bandwidth": int(fmt["abr"] * 1000),
        "lang": lang,
        "audioSamplingRate": fmt["asr"],
        "audioChannels": fmt.get("audio_channels", 2)
    }
    if (inputstream == "adaptive"):
        pref = fmt.get("language_preference", -1)
        original = (pref == 10)
        impaired = (pref == -10)
        stream.update(original=original, impaired=impaired)
        if track:
            stream["_default_"] = __adefault__(lang, track, codec, acodec)
        else:
            stream["default"] = original
    return stream


__streamTypes__ = {
    "video": __video_stream__,
    "audio": __audio_stream__
}


# ------------------------------------------------------------------------------

def __include__(contentType, codec, ocodec, exclude):
    if (
        codec and
        (codec != NoneCodec) and
        (ocodec == NoneCodec) and
        (not codec.startswith(exclude))
    ):
        return contentType
        #return (contentType, codec)


def __filter__(vcodec, acodec, exclude):
    return (
        __include__("video", vcodec, acodec, exclude) or
        __include__("audio", acodec, vcodec, exclude)
    )


def __dash__(formats, exclude):
    return (
        fmt for fmt in formats
        if (
            fmt.get("container", "").endswith("_dash") and
            fmt.setdefault(
                "__contentType__",
                __filter__(fmt.get("vcodec"), fmt.get("acodec"), exclude)
            )
            #fmt.setdefault(
            #    "__stream_args__",
            #    __filter__(fmt.get("vcodec"), fmt.get("acodec"), exclude)
            #)
        )
    )


# streams ----------------------------------------------------------------------

def __streams__(formats, exclude=None, **kwargs):
    for fmt in __dash__(formats, exclude or tuple()):
        contentType = fmt["__contentType__"]
        if (stream := __streamTypes__[contentType](fmt, **kwargs)):
            yield dict(
                stream,
                contentType=contentType,
                mimeType=f"{contentType}/{fmt['ext']}",
                id=fmt["format_id"],
                url=fmt["url"],
                indexRange=fmt.get("indexRange", {}),
                initRange=fmt.get("initRange", {})
            )


def __subtitles__(subtitles):
    return [
        dict(
            contentType="text",
            mimeType=f"text/{subtitle['ext']}",
            lang=subtitle["language"],
            id=subtitle["name"],
            url=subtitle["uri"]
        )
        for subtitle in subtitles
        if (not subtitle["protocol"])
    ]


def __defaults__(streams):
    for _type_ in ("audio", "video"):
        _streams_ = [s for s in streams if (s["contentType"] == _type_)]
        for _default_ in ((True, True), (True, False), (False, True)):
            _defaults_ = [
                _s_ for _s_ in _streams_ if (_s_.get("_default_") == _default_)
            ]
            if _defaults_:
                for _d_ in _defaults_:
                    _d_["default"] = True
                break
    #streams.sort(key=lambda x: x.get("default", False), reverse=True)


def streams(video, formats, subtitles, **kwargs):
    if (streams := list(__streams__(formats, **kwargs))):
        __defaults__(streams)
        streams.extend(__subtitles__(subtitles))
    return (video["duration"], streams)
