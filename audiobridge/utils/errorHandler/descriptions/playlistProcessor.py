#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from enum import Enum

from audiobridge.config.bot import cfg as bot_cfg


class PlaylistProcessor(Enum):
    EXCEED_DURATION    = f"Суммарная продолжительность будущих аудиозаписей не может превышать {bot_cfg.settings.max_video_duration // 3600} часа!"
    NO_AVAILABLE_PARTS = "В плейлисте отсутствуют доступные видео для загрузки"

    def __new__(cls, description: str):
        obj             = object.__new__(cls)
        obj._value_     = len(cls.__members__) + 4000
        obj.description = description
        return obj
