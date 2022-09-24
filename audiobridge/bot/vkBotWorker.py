#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import os
import threading
import vk_api
from vk_api.bot_longpoll import VkBotEventType

from audiobridge.tools.myVkBotLongPoll import MyVkBotLongPoll
from audiobridge.commands.user import UserCommands
from audiobridge.common.config import RequestIndex, Settings, BotAuth
from audiobridge.common import vars
from audiobridge.tools.sayOrReply import sayOrReply


logger        = logging.getLogger('logger')
request_conf  = RequestIndex()
settings_conf = Settings()
auth_conf     = BotAuth()

class VkBotWorker():
	"""Обработка пользовательских запросов.
	"""

	def __init__(self, program_version: str, vk_bot_auth: vk_api.VkApi):
		"""Инициализация класса VkBotWorker.

		Args:
			program_version (str): Версия бота.
			vk_bot_auth (vk_api.VkApi) Апи бота в группе Вк.
		"""
		self.program_version = program_version
		self.longpoll        = MyVkBotLongPoll(vk_bot_auth, auth_conf.BOT_ID)
		# Обработка невыполненных запросов после обновления, краша бота
		unanswered_messages  = vars.vk_bot.messages.getDialogs(unanswered=1)
		for user_message in unanswered_messages.get('items'):
			# Проверка на сообщение от пользователя, а не беседы
			msg_obj = user_message.get('message')
			if 'users_count' not in msg_obj:
				msg_obj['peer_id'] = msg_obj.pop('user_id')
				msg_obj['text']    = msg_obj.pop('body')
				self.message_handler(msg_obj)

	def command_handler(self, msg_options: list, user_id: int) -> bool:
		"""Обработка пользовательских команд.

		Args:
			msg_options (list): Сообщение пользователя в виде списка аргументов.
			user_id (int): Идентификатор пользователя.

		Returns:
			bool: Успешность обработки команды.
		"""
		if not msg_options:
			return False
		command = msg_options[0].strip().lower()
		if(command == UserCommands.CLEAR.value):
			vars.queueHandler.clear_pool(user_id)
			return True
		return False

	def vk_video_handler(self, video_url: str) -> str:
		"""Получения прямой ссылки из внутренней ссылки Вк для скачивания прикреплённого видео.

		Args:
			video_url (str): Внутренняя ссылка прикреплённого Вк видео.

		Returns:
			str: Прямая ссылка на скачивание прикреплённого видео.
		"""
		video_url = video_url[video_url.find(request_conf.INDEX_VK_VIDEO) + len(request_conf.INDEX_VK_VIDEO):]
		logger.debug(f'Vk video info: {video_url}')
		response = vars.vk_agent.video.get(videos = video_url)
		items = response.get('items')
		if not items:
			return ''
		return items[0].get('player')

	def message_handler(self, msg_obj: dict):
		"""Обработка пользовательских сообщений

		Args:
			msg_obj (dict): Объект сообщения.
		"""
		user_id    = msg_obj.get('peer_id')
		message_id = msg_obj.get('id')

		options = list(filter(None, msg_obj.get('text').split('\n')))
		logger.debug(f'New message: ({len(options)}) {options}')

		# Обработка команд
		if self.command_handler(options, user_id):
			logger.debug("Command was processed")
			return

		# Инициализация ячейки конкретного пользователя
		if not vars.userRequests.get(user_id):
			vars.userRequests[user_id] = 0
		# Проверка на текущую загрузку плейлиста
		if vars.userRequests.get(user_id) < 0:
			sayOrReply(user_id, 'Ошибка: Пожалуйста, дождитесь окончания загрузки плейлиста.')
			return
		# Проверка на максимальное число запросов за раз
		if vars.userRequests.get(user_id) == settings_conf.MAX_REQUESTS_QUEUE:
			sayOrReply(user_id, 'Ошибка: Кол-во ваших запросов в общей очереди не может превышать {0}.'.format(settings_conf.MAX_REQUESTS_QUEUE))
			return

		# Проверка на превышения числа возможных аргументов запроса
		if len(options) > 5:
			sayOrReply(user_id, 'Ошибка: Слишком много аргументов.', message_id)
			return
		# Проверка возможных приложений, если отсутствует какой-либо текст в сообщении
		if not options:
			attachment_info = msg_obj.get('attachments')
			# logger.debug(attachment_info)
			# Обработка приложений к сообщению
			if attachment_info:
				try:
					logger.debug(f'Attachments info: ({len(attachment_info)}) {attachment_info[0].get("type")}')

					attachment_type = attachment_info[0].get("type")
					if attachment_type == 'video':
						video_info     = attachment_info[0].get('video')
						video_owner_id = video_info.get('owner_id')
						video_id       = video_info.get('id')

						video = f'{video_owner_id}_{video_id}'
						logger.debug(f'Attachment video: {video}')
						options = [ f'https://{request_conf.INDEX_VK_VIDEO}{video}' ]

					elif attachment_type == 'link':
						options = [ attachment_info[0].get('link').get('url') ]

				except Exception as er:
					logger.warning(f'Attachment: {er}')
					sayOrReply(user_id, 'Ошибка: Невозможно обработать прикреплённое видео. Пришлите ссылку.', message_id)
					return
		# Безопасный метод проверки, как list.get()
		if not next(iter(options), '').startswith(request_conf.INDEX_URL):
			sayOrReply(user_id, 'Не обнаружена ссылка для скачивания.', message_id)
			return
		# Обработка запроса с плейлистом
		if request_conf.INDEX_PLAYLIST in options[0]:
			# Проверка на отсутствие других задач от данного пользователя
			if (vars.userRequests.get(user_id)):
				sayOrReply(user_id, 'Ошибка: Для загрузки плейлиста очередь запросов должна быть пуста.')
				return
			# Проверка на корректность запроса
			if len(options) != 2:
				msg_error = 'Ошибка: Не указаны номера загружаемых видео.' if len(options) < 2 else 'Ошибка: Слишком много параметров для загрузки плейлиста.'
				sayOrReply(user_id, msg_error, message_id)
				return
			# Создание задачи + вызов функции фрагментации плейлиста, чтобы свести запрос к обычной единице (одной ссылке)
			vars.userRequests[user_id] = -1
			msg_start_id = sayOrReply(user_id, 'Запрос добавлен в очередь (плейлист)')
			task         = [[msg_start_id, user_id, message_id], options]
			threading.Thread(target = vars.audioTools.playlist_processing(task)).start()
			return
		# Обработка обычного запроса
		# Обработка YouTube Shorts
		if request_conf.INDEX_YOUTUBE_SHORTS in options[0]:
			logger.debug("Обнаружен YouTube Shorts. Замена ссылки...")
			options[0] = options[0].replace(request_conf.INDEX_YOUTUBE_SHORTS, "/watch?v=")
		# Обработка Vk Video
		elif request_conf.INDEX_VK_VIDEO in options[0]:
			logger.debug("Обнаружено Vk video. Получение прямой ссылки...")
			video_url = self.vk_video_handler(options[0].strip())
			if not video_url:
				sayOrReply(user_id, 'Ошибка: Невозможно обработать прикреплённое видео, т.к. оно скрыто настройками приватности автора', message_id)
				return
			options[0] = video_url
		# Создание задачи и её добавление в обработчик очереди
		vars.userRequests[user_id] += 1
		msg_start_id = sayOrReply(user_id, 'Запрос добавлен в очередь ({0}/{1})'.format(vars.userRequests.get(user_id), settings_conf.MAX_REQUESTS_QUEUE))
		task         = [[msg_start_id, user_id, message_id], options]
		vars.queueHandler.add_new_request(task)

	def listen_longpoll(self):
		"""Прослушивание новых сообщений от пользователей.
		"""
		for event in self.longpoll.listen():
			if event.type != VkBotEventType.MESSAGE_NEW:
				continue
			msg_obj = event.obj.message
			# Проверка на сообщение от пользователя, а не беседы
			# logger.debug(f'Получено новое сообщение: {msg_obj}')
			if msg_obj.get('from_id') == msg_obj.get('peer_id'):
				self.message_handler(msg_obj)
