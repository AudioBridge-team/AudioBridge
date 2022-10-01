#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import subprocess
from audiobridge.common import vars
from audiobridge.common.config import VkGroup, BotAuth
from audiobridge.tools.customErrors import CustomError

logger = logging.getLogger('logger')
vkgroup_conf = VkGroup()
auth_conf    = BotAuth()

class VkGroupManager():
	def __init__(self):
		logger.info(f'Synchronize vk changelog is: {vkgroup_conf.SYNC_CHANGELOG}')
		logger.info(f'Release vk post-update is: {vkgroup_conf.RELEASE_UPDATE}')
		if vkgroup_conf.SYNC_CHANGELOG:
			self._sync_changelog()

	def _fix_wiki_for_vk(self, wiki: str) -> str:
		# удаление переноса строки после заголовков
		# добавление ещё одного знака = для заголовков
		# добавление знака | в заголовках с ссылками
		return wiki

	def _sync_changelog(self):
		try:
			if vkgroup_conf.CHANGELOG_PAGE_ID == -1:
				raise CustomError("Can't get changelog page id. Changelog wasn't synchronized!")

			# proc = subprocess.Popen("pandoc CHANGELOG.md -t mediawiki", stdout = subprocess.PIPE, stderr = subprocess.PIPE, text = True, shell = True)
			# stdout, stderr = proc.communicate()
			# if stderr:
			# 	raise CustomError(f"Can't convert .md to .wiki: {stderr}")
			# if not stdout:
			# 	raise CustomError('CHANGELOG.wiki is empty!')

			# vars.vk_agent.pages.save(text=stdout, page_id=vkgroup_conf.CHANGELOG_PAGE_ID, group_id=auth_conf.BOT_ID)

			with open("CHANGELOG.wiki", "r", encoding="utf-8") as file:
				wiki = file.read()
				logger.debug(self._fix_wiki_for_vk)

		except CustomError as er:
			logger.error(f'Custom: {er}')
		except Exception as er:
			logger.error(f"Can't update vk changelog: {er}")
