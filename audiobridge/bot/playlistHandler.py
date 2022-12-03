#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import yt_dlp

from audiobridge.tools.customErrors import CustomError, specific_errors
from audiobridge.common.config import Settings, PlaylistStates, ParametersType
from audiobridge.common import vars
from audiobridge.tools.sayOrReply import sayOrReply
from audiobridge.tools.yt_dlpShell import Yt_dlpShell


logger        = logging.getLogger('logger')
settings_conf = Settings()
playlist_conf = PlaylistStates()
param_type    = ParametersType()
MSG_REPLY     = 'msg_reply'
# Опции для модуля yt_dlp
ydl_opts = {
    'logger': Yt_dlpShell(),
	"extract_flat": True,
    'nocheckcertificate': True,
    'retries': settings_conf.MAX_ATTEMPTS
}

class PlaylistHandler():
	"""Класс вспомогательных инструментов для обработки запроса.

	Raises:
		CustomError: Вызов ошибки с настраиваемым содержанием.
	"""
	def __init__(self):
		"""Инициализация класса PlaylistHandler.
		"""
		self.playlist_result = {}

	def extract_elements(self, task: dict):
		"""Обработка плейлиста: извлечение его составляющих.

		Args:
			task (dict): Пользовательский запрос.

		Raises:
			CustomError:  Вызов ошибки с настраиваемым содержанием.
		"""
		logger.debug(f'Получил плейлист: {task}')

		msg_start = task.get(param_type.MSG_START) 	# id сообщения с размером очереди (необходимо для удаления в конце обработки запроса)
		user_id   = task.get(param_type.USER_ID) 	# id пользователя
		msg_reply = task.get(param_type.MSG_REPLY) 	# id сообщения пользователя (необходимо для ответа на него)

		pl_url    = task.get(param_type.URL) 	    # Ссылка на плейлист
		pl_param  = task.get(param_type.PL_PARAM) 	# Параметры для скачивания плейлиста (количество и/или номера песен в плейлисте)

		urls = [] # url составляющих плейлист
		try:
			totalTime = 0
			# Проверка на наличие строки в запросе с номерами необходимых элементов плейлиста
			if pl_param:
				ydl_opts['playlist_items'] = pl_param
			# Извлечение полной информации о всех доступных и недоступных видео из плейлиста
			pl_info = yt_dlp.YoutubeDL(ydl_opts).extract_info(pl_url, download=False)
			for entry in pl_info['entries']:
				if not entry: continue
				url = entry.get("url", None)
				title = entry.get("title", None)
				if not (url and title): continue
				urls.append([url, title])

				duration = entry.get("duration", None)
				totalTime += int(float(duration))
				if totalTime > settings_conf.MAX_VIDEO_DURATION:
					raise CustomError(f'Ошибка: {specific_errors.get("MAX_VIDEO_DURATION")}')

			if not urls:
				raise CustomError('Ошибка: В плейлисте отсутствуют доступные видео для загрузки.')
			vars.vk_bot.messages.edit(peer_id = user_id, message = f'Запрос добавлен в очередь (плейлист: {len(urls)})', message_id = msg_start)

		except CustomError as er:
			sayOrReply(user_id, er, msg_reply)

			# Удаление сообщения с порядком очереди
			vars.vk_bot.messages.delete(delete_for_all = 1, message_ids = msg_start)
			# Очистка памяти, т.к. переменная пуста
			del vars.userRequests[user_id]
			logger.error(f'Custom: {er}')

		except Exception as er:
			error_string = 'Ошибка: Невозможно обработать плейлист. Убедитесь, что запрос корректный и отправьте его повторно.'
			sayOrReply(user_id, error_string, msg_reply)

			# Удаление сообщения с порядком очереди
			vars.vk_bot.messages.delete(delete_for_all = 1, message_ids = msg_start)
			del vars.userRequests[user_id]
			logger.error(f'Поймал исключение: {er}')

		else:
			self.playlist_result[user_id] = {MSG_REPLY : msg_reply}  # Отчёт скачивания плейлиста
			for i, url in enumerate(urls):
				self.playlist_result[user_id][i+1] = [playlist_conf.PLAYLIST_UNSTATED, url[1]]
				vars.userRequests[user_id] -= 1
				sub_task = task.copy()
				sub_task.update({ param_type.URL: url[0], param_type.PL_ELEMENT: i+1, param_type.PL_SIZE: len(urls) })
				vars.queueHandler.add_new_request(sub_task)

	def summarize(self, user_id: int):
		"""Подведение отчёта об обработки плейлиста.

		Args:
			user_id (_type_): Идентификатор пользователя.
		"""
		try:
			if self.playlist_result.get(user_id):
				msg_summary = ""
				summary     = {}
				msg_reply      = self.playlist_result[user_id][MSG_REPLY]

				for task_id, info in self.playlist_result[user_id].items():
					if task_id == MSG_REPLY:
						continue
					if not summary.get(info[0]):
						summary[info[0]] = [info[1]]
					else:
						summary[info[0]].append(info[1])
				logger.debug(f'Сводка по плейлисту: {summary}')

				if summary.get(playlist_conf.PLAYLIST_SUCCESSFUL):
					msg_summary += 'Успешно:\n'
					for title in summary[playlist_conf.PLAYLIST_SUCCESSFUL]: msg_summary += ('• ' + title + '\n')
				if summary.get(playlist_conf.PLAYLIST_COPYRIGHT):
					msg_summary += '\nЗаблокировано из-за авторских прав:\n'
					for title in summary[playlist_conf.PLAYLIST_COPYRIGHT]: msg_summary += ('• ' + title + '\n')
				if summary.get(playlist_conf.PLAYLIST_UNSTATED):
					msg_summary += '\nНе загружено:\n'
					for title in summary[playlist_conf.PLAYLIST_UNSTATED]: msg_summary += ('• ' + title + '\n')
				del self.playlist_result[user_id]
				sayOrReply(user_id, msg_summary, msg_reply)

		except Exception as er:
			logger.error(er)
			sayOrReply(user_id, 'Ошибка: Не удалось загрузить отчёт.')
