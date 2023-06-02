#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from vk_api.keyboard import *
from dataclasses import dataclass


class KeyboardKeys:
    CMD : str = "command"
    ARGS: str = "args"

keys = KeyboardKeys

@dataclass(init=False)
class Keyboard:
    """Класс-шаблон для клавиатур.
    """
    command: str

    def keyboard(self, *args):
        """Функция, описывающая клавиатуру.
        """
        raise NotImplementedError()
