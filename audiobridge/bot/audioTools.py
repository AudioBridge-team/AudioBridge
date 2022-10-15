#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import time
import subprocess
import json

from audiobridge.tools.customErrors import CustomError
from audiobridge.common.config import Settings, PlaylistStates
from audiobridge.common import vars
from audiobridge.tools.sayOrReply import sayOrReply


logger = logging.getLogger('logger')
settings_conf = Settings()
playlist_conf = PlaylistStates()

cmdPlaylistInfo = lambda filter, url: 'youtube-dl --no-warnings --dump-json --newline {0} "{1}"'.format(filter, url) # Получение информации о компонентах плейлиста

class AudioTools():
	"""Класс вспомогательных инструментов для обработки запроса.

	Raises:
		CustomError: Вызов ошибки с настраиваемым содержанием.
	"""
	def __init__(self):
		"""Инициализация класса AudioTools.
		"""
		self.playlist_result = {}

	def _getPlaylistElements(self, cmd: str, attempts = 0) -> list:
		"""Получение url компонентов плейлиста, а также проверка их общей продолжительности.

		Args:
			cmd (str): Команда для получения информации о каждом компоненте плейлиста.
			attempts (int, optional): Количество попыток неуспешного выполнения команды. Defaults to 0.

		Raises:
			CustomError:  Вызов ошибки с настраиваемым содержанием.

		Returns:
			list: Список url компонентов плейлиста.
		"""
		urls = []
		totalTime = 0
		# Выход из рекурсии, если превышено число попыток выполнения команды
		if attempts == settings_conf.MAX_ATTEMPTS:
			raise CustomError('Ошибка обработки плейлиста.')
		# Получение urls и проверка общей продолжительности запроса
		proc = subprocess.Popen(cmd, stdout = subprocess.PIPE, stderr = subprocess.PIPE, text = True, shell = True)
		line = str(proc.stdout.readline())
		while line:
			obj = json.loads(line.strip())
			totalTime += int(float(obj['duration']))
			if totalTime > settings_conf.MAX_VIDEO_DURATION:
				raise CustomError('Ошибка: Суммарная продолжительность будущих аудиозаписей не может превышать 3 часа!')
			urls.append([obj['webpage_url'], obj['title'].strip()])
			line = str(proc.stdout.readline())
		stderr = proc.communicate()[1].strip()
		if stderr:
			logger.error(f'Getting playlist information ({attempts}): {stderr}')
			# Данная ошибка может произойти неожиданно, поэтому приходится повторять попытку выполнения команды через определённое время
			if ('http error 403' in stderr.lower()):
				attempts += 1
				time.sleep(settings_conf.TIME_ATTEMPT)
				self._getPlaylistElements(cmd, attempts)
			elif ('sign in to confirm your age' in stderr.lower()):
				raise CustomError('Ошибка: Невозможно скачать плейлист из-за возрастных ограничений.')
			elif ('video unavailable' in stderr.lower()):
				raise CustomError('Ошибка: Плейлист недоступен из-за авторских прав или по иным причинам.')
			elif ('valueerror: invalid literal for int() with base 10' in stderr.lower()):
				raise CustomError('Ошибка: Неверный формат второго аргумента (количество скачиваемых аудио).')
			else:
				raise CustomError('Ошибка: Неверные параметры скачивания и/или URL плейлиста.')

		# Проверка наличия результатов работы команды
		if not urls or not totalTime:
			attempts += 1
			logger.error(f"Ошибка получения информации об плейлисте ({attempts}):\n\tTotal time:{totalTime}")
			time.sleep(settings_conf.TIME_ATTEMPT)
			self._getPlaylistElements(cmd, attempts)
		# Выход из рекурсии, если информация была успешно получена
		return urls

	def playlist_processing(self, task: dict):
		"""Обработка плейлиста: извлечение его составляющих.

		Args:
			task (dict): Пользовательский запрос.

		Raises:
			CustomError:  Вызов ошибки с настраиваемым содержанием.
		"""
		logger.debug(f'Получил плейлист: {task}')
		param        = task[0]
		options      = task[1]   # Параметры запроса
		msg_start_id = param[0]  # id сообщения с размером очереди (необходимо для удаления в конце обработки запроса)
		user_id      = param[1]  # id пользователя
		msg_id       = param[2]  # id сообщения пользователя (необходимо для ответа на него)

		urls = [] # url составляющих плейлист
		try:
			informationString = ""
			if (options[1].isdigit()):
				informationString = cmdPlaylistInfo(f'--max-downloads {options[1]}', options[0])
			elif (options[1][-1] == '-'):
				start_playlist = options[1][:1]
				informationString = cmdPlaylistInfo(f'--playlist-start {start_playlist}', options[0])
			else:
				informationString = cmdPlaylistInfo(f'--playlist-items {str(options[1]).replace(" ", "")}', options[0])

			urls = self._getPlaylistElements(informationString)

			vars.vk_bot.messages.edit(peer_id = user_id, message = f'Запрос добавлен в очередь (плейлист: {len(urls)})', message_id = msg_start_id)

		except CustomError as er:
			sayOrReply(user_id, er, msg_id)

			# Удаление сообщения с порядком очереди
			vars.vk_bot.messages.delete(delete_for_all = 1, message_ids = msg_start_id)
			# Очистка памяти, т.к. переменная пуста
			del vars.userRequests[user_id]
			logger.error(f'Custom: {er}')

		except Exception as er:
			error_string = 'Ошибка: Невозможно обработать плейлист. Убедитесь, что запрос корректный и отправьте его повторно.'
			sayOrReply(user_id, error_string, msg_id)

			# Удаление сообщения с порядком очереди
			vars.vk_bot.messages.delete(delete_for_all = 1, message_ids = msg_start_id)
			del vars.userRequests[user_id]
			logger.error(f'Поймал исключение: {er}')

		else:
			self.playlist_result[user_id] = {'msg_id' : msg_id}  # Отчёт скачивания плейлиста
			for i, url in enumerate(urls):
				self.playlist_result[user_id][url[1]] = playlist_conf.PLAYLIST_UNSTATED
				vars.userRequests[user_id] -= 1
				vars.queueHandler.add_new_request([param, [url[0]], [i+1, len(urls)]])

	def playlist_summarize(self, user_id: int):
		"""Подведение отчёта об обработки плейлиста.

		Args:
			user_id (_type_): Идентификатор пользователя.
		"""
		try:
			if self.playlist_result.get(user_id):
				msg_summary = ""
				summary     = {}
				msg_id      = self.playlist_result[user_id]['msg_id']

				for title, status in self.playlist_result[user_id].items():
					if status == msg_id:
						continue
					if not summary.get(status):
						summary[status] = [title]
					else:
						summary[status].append(title)
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
				sayOrReply(user_id, msg_summary, msg_id)

		except Exception as er:
			logger.error(er)
			sayOrReply(user_id, 'Ошибка: Не удалось загрузить отчёт.')
