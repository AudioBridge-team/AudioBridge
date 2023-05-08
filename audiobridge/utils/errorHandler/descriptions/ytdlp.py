#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from enum import Enum


class Ytdlp(Enum):
    UNDEFINED       = "",                                                               "Возникла непредвиденная ошибка при обработке запроса. Обратитесь к разработчикам"
    BAD_URL         = "is not a valid url",                                             "Некорректный адрес источника"
    HTTP_404        = "http error 404",                                                 "Некорректный адрес источника"
    NO_PLAYLIST     = "the channel/playlist does not exist",                            "Данный плейлист не существует"
    BAD_SPECIF      = "is not a valid specification",                                   "Некорректный адрес источника"
    UNABLE_DOWNLAOD = "unable to download webpage",                                     "Некорректный адрес источника"
    ADULT_CONTENT   = "this video was marked as adult content",                         "VK заблокировал обработку видео из-за наличия взрослого контента"
    UNSUPPORTED_URL = "unsupported url",                                                "Данный URL не поддерживается"
    BLOCKED_COUNTRY = "the uploader has not made this video available in your country", "Правообладатель ограничил доступ к материалу в стране, где располагается сервер"
    LEGAL_COMPLAINT = "is not available in your country due to a legal complaint",      "Из-за юридической жалобы видео недоступно в стране, в которой располагается сервер"
    UNAVAILABLE_1   = "this video is not available",                                    "Видео недоступно"
    COPYRIGHT       = "who has blocked it in your country on copyright",                "Видео содержит заблокированный контент для страны, в которой располагается сервер"
    BAD_TIMINGS     = "since chapter information is unavailable",                       "Видео не содержит эпизодов, используйте тайминги"
    BAD_EPISODE     = "no chapters matching the regex",                                 "Данного эпизода не существует. Проверьте корректность его написания"
    UNAVAILABLE_2   = "video unavailable",                                              "Видео недоступно"

    def __new__(cls, key: str, description: str):
        obj             = object.__new__(cls)
        obj.key         = key
        obj._value_     = len(cls.__members__) + 6000
        obj.description = description
        return obj
