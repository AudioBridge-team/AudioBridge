#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from enum import Enum


class QueueProcessor(Enum):
    ALREADY_EMPTY        = "Очередь запросов уже пуста"
    CANT_CLEAN           = "Не удалось почистить очередь"

    def __new__(cls, description: str):
        obj             = object.__new__(cls)
        obj._value_     = len(cls.__members__) + 3000
        obj.description = description
        return obj
