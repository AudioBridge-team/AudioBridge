#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from dataclasses import dataclass


@dataclass
class VkGroup:
    """Настройка информирования подписчиков в группе.
    """
    sync_changelog   : bool
    release_update   : bool
    changelog_page_id: int


with open("bot_settings.json", "r") as f:
    settings_json = json.load(f)

cfg = VkGroup(
    sync_changelog    = settings_json.get("sync_changelog", False),
    release_update    = settings_json.get("release_update", False),
    changelog_page_id = settings_json.get("changelog_page_id", -1)
)
