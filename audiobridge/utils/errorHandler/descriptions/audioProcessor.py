#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from enum import Enum


class AudioProcessor(Enum):
    STOP_THREAD        = ""
    NO_INFO            = "Невозможно получить информацию о видео"
    BAD_TIME_FORMAT    = "Неверный формат времени среза"
    INCORRECT_TIME     = "Некорректное время среза"
    INCORRECT_DURATION = "Некорректная продолжительность среза"
    HIGH_PREV_SIZE     = "Размер аудиозаписи превышает 200 Мб"
    HIGH_REAL_SIZE     = "Размер аудиозаписи превышает 200 Мб"

    def __new__(cls, description: str):
        obj             = object.__new__(cls)
        obj._value_     = len(cls.__members__) + 5000
        obj.description = description
        return obj
