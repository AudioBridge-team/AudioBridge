#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
from vk_api.bot_longpoll import VkBotLongPoll


logger = logging.getLogger('logger')

class MyVkBotLongPoll(VkBotLongPoll):
	"""Обработчик событий от VkBotLongPoll.

	Args:
		VkBotLongPoll (VkBotLongPoll): VkBotLongPoll.

	Yields:
		VkBotMessageEvent: VkBotMessageEvent
	"""

	def listen(self):
		while True:
			try:
				for event in self.check():
					yield event
			except Exception as er:
				logger.error(f'VK LONGPOLL ({er.code}): {er}')
