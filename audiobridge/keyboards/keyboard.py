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
    command: str
    executable: bool = False

    def keyboard(self, *args):
        raise NotImplementedError()
