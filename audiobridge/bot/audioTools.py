#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import datetime, time
import subprocess
import json

from audiobridge.bot.customErrors import CustomError
from audiobridge.common.config import Settings, PlaylistStates
from audiobridge.common import constants as const
from audiobridge.common.sayOrReply import sayOrReply


logger = logging.getLogger('logger')

class AudioTools():
	"""Класс вспомогательных инструментов для обработки запроса.

	Raises:
		CustomError: Вызов ошибки с настраиваемым содержанием.
	"""
	def __init__(self):
		"""Инициализация класса AudioTools.
		"""
		self.playlist_result = {}

	def getSeconds(self, strTime: str) -> int:
		"""Обработка строки со временем; в скором времени откажемся от этой функции.

		Args:
			strTime (str): Строка со временем.

		Returns:
			int: Время в секундах.
		"""
		strTime = strTime.strip()
		try:
			pattern = ''
			if strTime.count(':') == 1:
				pattern = '%M:%S'
			if strTime.count(':') == 2:
				pattern = '%H:%M:%S'
			if pattern:
				time_obj = datetime.strptime(strTime, pattern)
				return time_obj.hour * 60 * 60 + time_obj.minute * 60 + time_obj.second
			else:
				return int(float(strTime))
		except Exception as er:
			logger.error(er)
			return -1

	def getVideoInfo(self, key: str, url: str) -> str:
		"""Получение строки для извлечения определённой информацию о видео по ключу.

		Args:
			key (str): Информация, нужно узнать.
			url (str): Ссылка на видео.

		Returns:
			str: Строка для извлечения определённой информацию о видео по ключу.
		"""
		return 'youtube-dl --max-downloads 1 --no-warnings --get-filename -o "%({0})s" "{1}"'.format(key, url)

	def getPlaylistInfo(self, filter: str, url: str) -> str:
		"""Получение строки для извлечения элементов из плейлиста.

		Args:
			filter (str): Фильтр элементов.
			url (str): Ссылка на плейлист.

		Returns:
			str: Строка для извлечения извлечения элементов из плейлиста.
		"""
		return 'youtube-dl --no-warnings --dump-json --newline {0} {1}'.format(filter, url)

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

		urls = []  # url составляющих плейлист
		try:
			informationString = ''
			if (options[1].isdigit()):
				informationString = self.getPlaylistInfo(f'--max-downloads {options[1]}', options[0])
			elif (options[1][-1] == '-'):
				start_playlist = options[1][:1]
				informationString = self.getPlaylistInfo(f'--playlist-start {start_playlist}', options[0])
			else:
				informationString = self.getPlaylistInfo(f'--playlist-items {options[1]}', options[0])
			totalTime = 0
			attempts = 0

			# Получение urls и проверка общей продолжительности запроса
			while attempts != Settings.MAX_ATTEMPTS:
				proc = subprocess.Popen(informationString, stdout = subprocess.PIPE, stderr = subprocess.PIPE, text = True, shell = True)
				line = str(proc.stdout.readline())
				while line:
					obj = json.loads(line.strip())
					totalTime += int(float(obj['duration']))
					if (totalTime > Settings.MAX_VIDEO_DURATION):
						raise CustomError('Ошибка: Суммарная продолжительность будущих аудиозаписей не может превышать 3 часа!')
					urls.append([obj['webpage_url'], obj['title'].strip()])
					line = str(proc.stdout.readline())
				stdout, stderr = proc.communicate()

				# Выход из цикла, если информация была успешно получена
				if (not stderr and urls):
					break

				logger.error(f'Getting playlist information ({attempts}): {stderr.strip()}')
				if ('HTTP Error 403' in stderr):
					attempts += 1
					time.sleep(Settings.TIME_ATTEMPT)
					continue
				elif ('Sign in to confirm your age' in stderr):
					raise CustomError('Ошибка: Невозможно скачать плейлист из-за возрастных ограничений.')
				elif ('Video unavailable' in stderr):
					raise CustomError('Ошибка: Плейлист недоступен из-за авторских прав или по иным причинам.')
				else:
					raise CustomError('Ошибка: Неверные параметры скачивания и/или URL плейлиста.')

			if not totalTime:
				raise CustomError('Ошибка обработки плейлиста.')

			const.vk_bot.messages.edit(peer_id = user_id, message = f'Запрос добавлен в очередь (плейлист: {len(urls)})', message_id = msg_start_id)

		except CustomError as er:
			sayOrReply(user_id, f'Произошла ошибка: {er}', msg_id)

			# Удаление сообщения с порядком очереди
			const.vk_bot.messages.delete(delete_for_all = 1, message_ids = msg_start_id)
			del const.userRequests[user_id]
			logger.error(f'Произошла ошибка: {er}')

		except Exception as er:
			error_string = 'Ошибка: Невозможно обработать плейлист. Убедитесь, что запрос корректный и отправьте его повторно.'
			sayOrReply(user_id, error_string, msg_id)

			# Удаление сообщения с порядком очереди
			const.vk_bot.messages.delete(delete_for_all = 1, message_ids = msg_start_id)
			del const.userRequests[user_id]
			logger.error(f'Поймал исключение: {er}')

		else:
			self.playlist_result[user_id] = {'msg_id' : msg_id}  # Отчёт скачивания плейлиста
			for i, url in enumerate(urls):
				self.playlist_result[user_id][url[1]] = PlaylistStates.PLAYLIST_UNSTATED
				const.userRequests[user_id] -= 1
				const.queueHandler.add_new_request([param, [url[0]], [i+1, len(urls)]])

	def playlist_summarize(self, user_id: int):
		"""Подведение отчёта об обработки плейлиста.

		Args:
			user_id (_type_): Идентификатор пользователя.
		"""
		try:
			if self.playlist_result.get(user_id):
				msg_summary = ''
				summary     = {}
				msg_id      = self.playlist_result[user_id]['msg_id']

				for title, status in self.playlist_result[user_id].items():
					if status == msg_id: continue
					if not summary.get(status):
						summary[status] = [title]
					else:
						summary[status].append(title)
				logger.debug(f'Сводка по плейлисту: {summary}')

				if summary.get(PlaylistStates.PLAYLIST_SUCCESSFUL):
					msg_summary += 'Успешно:\n'
					for title in summary[PlaylistStates.PLAYLIST_SUCCESSFUL]: msg_summary += ('• ' + title + '\n')
				if summary.get(PlaylistStates.PLAYLIST_COPYRIGHT):
					msg_summary += '\nЗаблокировано из-за авторских прав:\n'
					for title in summary[PlaylistStates.PLAYLIST_COPYRIGHT]: msg_summary += ('• ' + title + '\n')
				if summary.get(PlaylistStates.PLAYLIST_UNSTATED):
					msg_summary += '\nНе загружено:\n'
					for title in summary[PlaylistStates.PLAYLIST_UNSTATED]: msg_summary += ('• ' + title + '\n')
				del self.playlist_result[user_id]
				sayOrReply(user_id, msg_summary, msg_id)

		except Exception as er:
			logger.error(er)
			sayOrReply(user_id, 'Ошибка: Не удалось загрузить отчёт.')
