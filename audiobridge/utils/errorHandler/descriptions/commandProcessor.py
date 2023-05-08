#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from enum import Enum


class CommandProcessor(Enum):
    BAD_COMMAND = "Данной команды не существует. Введите /help для просмотра доступных команд"
    BAD_FORMAT  = "Неправильный формат команды. Узнайте правильный с помощью /help"
    NO_TOKEN    = "Вы не авторизованы в боте"

    def __new__(cls, description: str):
        obj             = object.__new__(cls)
        obj._value_     = len(cls.__members__) + 7000
        obj.description = description
        return obj
