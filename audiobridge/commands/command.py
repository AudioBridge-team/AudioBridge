#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from dataclasses import dataclass
from enum import IntEnum, auto

from audiobridge.db.dbEnums import UserRoles

class CommandCategory(IntEnum):
    """Категория команды.

    Args:
        IntEnum (_type_): Порядковый номер.

    Returns:
        Enum: Порядковый номер и описание категории команды.
    """
    API      = "Работа с ботом"
    QUEUE    = "Управление загрузками"
    SETTINGS = "Настройка аккаунта"

    def __new__(cls, description: str):
        obj             = int.__new__(cls)
        obj._value_     = auto()
        obj.description = description
        return obj

@dataclass(init=False)
class Command:
    """Класс-родитель, описывающий скелет пользовательских команд.
    """
    name       : str
    description: str
    category   : CommandCategory
    userRole   : UserRoles = UserRoles.USER

    def run(self, *args):
        """Функция для конкретной команды.

        Raises:
            NotImplementedError: Вызов несуществующей функции.
        """
        raise NotImplementedError()
