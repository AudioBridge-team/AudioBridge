#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from dataclasses import dataclass
from enum import IntEnum, auto

class CommandCategory(IntEnum):
    """Категория команды.

    Args:
        IntEnum (_type_): Порядковый номер.

    Returns:
        Enum: Порядковый номер и описание категории команды.
    """
    API      = auto(), "Работа с ботом"
    QUEUE    = auto(), "Управление загрузками"
    SETTINGS = auto(), "Настройка аккаунта"

    def __new__(cls, value: int, description: str):
        obj             = int.__new__(cls)
        obj._value_     = value
        obj.description = description
        return obj

@dataclass(init=False)
class Command:
    """Класс-родитель, описывающий скелет пользовательских команд.
    """
    name       : str
    description: str
    category   : CommandCategory
    adminOnly  : bool

    def run(self, *args):
        """Функция для конкретной команды.

        Raises:
            NotImplementedError: Вызов несуществующей функции.
        """
        raise NotImplementedError()
