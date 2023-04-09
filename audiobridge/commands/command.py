#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from enum import IntEnum, auto

class CommandCategory(IntEnum):
    SETTINGS = auto()
    QUEUE = auto()
    API = auto()

class Command:
    def __init__(self, name: str, description: str, category: CommandCategory, adminOnly: bool):
        self.name = name
        self.description = description
        self.category = category
        self.adminOnly = adminOnly

    def run(self, *args):
        raise NotImplementedError()
