#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
from audiobridge.common import vars
from audiobridge.common.config import VkGroup, BotAuth

logger = logging.getLogger('logger')
vkgroup_conf = VkGroup()
auth_conf    = BotAuth()

class VkGroupManager():
	def __init__(self):
		logger.info(f'Synchronize vk changelog is: {vkgroup_conf.SYNC_CHANGELOG}')
		logger.info(f'Release vk post-update is: {vkgroup_conf.RELEASE_UPDATE}')
		if vkgroup_conf.SYNC_CHANGELOG:
			self._sync_changelog()

	def _convert_to_wiki(self, body: str) -> str:
		return body

	def _sync_changelog(self):
		if vkgroup_conf.CHANGELOG_PAGE_ID == -1:
			logger.error("Can't get changelog page id. Changelog wasn't synchronized!")
			return
		try:
			changelog = ""
			with open("CHANGELOG.md", "r", encoding="utf-8") as file:
				changelog = self._convert_to_wiki(file.read())
			logger.debug(changelog)
			# vars.vk_agent.pages.save(text = "ok", page_id=vkgroup_conf.CHANGELOG_PAGE_ID, group_id=auth_conf.BOT_ID)
		except Exception as er:
			logger.error(f"Can't update vk changelog: {er}")
