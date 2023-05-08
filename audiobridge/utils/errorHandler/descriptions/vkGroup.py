#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from enum import Enum


class VkGroup(Enum):
    NO_CHANGELOG_ID = "Changelog page id isn't set. Changelog wasn't synchronized!"
    CANT_CONVERT    = "Can't convert .md to .wiki"
    EMPTY_CHANGELOG = "CHANGELOG.wiki is empty"

    def __new__(cls, description: str):
        obj             = object.__new__(cls)
        obj._value_     = len(cls.__members__) + 2000
        obj.description = description
        return obj
