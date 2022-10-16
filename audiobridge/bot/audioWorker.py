#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import os
import threading, subprocess
import time
from datetime import datetime

import vk_api
from vk_api.utils import get_random_id

from audiobridge.tools.customErrors import CustomError, CustomErrorCode

from audiobridge.common.config import Settings, PlaylistStates
from audiobridge.common import vars
from audiobridge.tools.sayOrReply import sayOrReply


logger = logging.getLogger('logger')
settings_conf = Settings()
playlist_conf = PlaylistStates()

cmdAudioUrl  = lambda url: 'youtube-dl --max-downloads 1 --no-warnings --get-url --extract-audio "{0}"'.format(url)				# Команда получения прямой ссылки аудио
cmdAudioInfo = lambda url: 'ffmpeg -loglevel info -hide_banner -i "{0}"'.format(url) 											# Команда получения полной информации об аудио (нас интересует только продолжительность и битрейт)
cmdVideoInfo = lambda key, url: 'youtube-dl --max-downloads 1 --no-warnings --get-filename -o "%({0})s" "{1}"'.format(key, url)	# Команда получения информации о видео по ключу

class AudioWorker(threading.Thread):
	"""Аудио воркер — класс скачивания песен и загрузки в Вк.

	Args:
		threading.Thread (threading.Thread): threading.Thread

	Raises:
		CustomError: Вызов ошибки с настраиваемым содержанием.
	"""

	def __init__(self, task: list):
		"""Инициализация класса AudioWorker.

		Args:
			task (list): Пользовательский запрос.
		"""
		super(AudioWorker, self).__init__()
		self._stop     = False
		self._task     = task
		self._playlist = False

	def _toSeconds(self, strTime: str) -> int:
		"""Обработка строки со временем.

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
		except ValueError as er:
			logger.error(f"Wrong time: {strTime}")
			return -1
		except Exception as er:
			logger.error(er)
			return -1

	def _getAudioInfo(self, origin_url: str, attempts = 0) -> tuple:
		"""Извлечение продолжительности и битрейта аудио.

		Args:
			cmd (str): Команда для извлечения информации об аудио.
			attempts (int, optional): Количество попыток неуспешного выполнения команды. Defaults to 0.

		Raises:
			CustomError: Вызов ошибки с настраиваемым содержанием.

		Returns:
			tuple: (продолжительность аудио в сек., битрейт аудио в кб/c)
		"""
		# Выход из рекурсии, если пользователь отменил выполнение запроса
		if self._stop:
			raise CustomError(code=CustomErrorCode.STOP_THREAD)
		# Выход из рекурсии, если превышено число попыток выполнения команды
		if attempts == settings_conf.MAX_ATTEMPTS:
			raise CustomError("Ошибка: Невозможно получить информацию о видео.")
		# Проверка на существование прямой ссылки
		if not self.url:
			# Получение прямой ссылки аудио
			self.url = self._getAudioUrl(cmdAudioUrl(origin_url))

		proc = subprocess.Popen(cmdAudioInfo(self.url), stderr = subprocess.PIPE, text = True, shell = True)
		audioInfo = proc.communicate()[1].strip()
		# Данная ошибка может произойти неожиданно, поэтому приходится повторять попытку выполнения команды через определённое время
		if ('http error 403' in audioInfo.lower()) or audioInfo.find("Duration:") == -1:
			attempts += 1
			logger.error(f"Ошибка получения информации об аудио ({attempts}):\n{audioInfo}")
			# Обнуление прямой ссылки для получения новой
			self.url = ""
			time.sleep(settings_conf.TIME_ATTEMPT)
			self._getAudioInfo(origin_url, attempts)

		audioInfo = audioInfo[audioInfo.find("Duration:"):]
		audioInfo = audioInfo[:audioInfo.find('\n')]
		audioInfo = audioInfo.split(',')
		duration = audioInfo[0][audioInfo[0].find(':')+2:]
		# Отсекание дробной части
		if '.' in duration:
			duration = duration[:duration.find(".")]
		bitrate = audioInfo[2][audioInfo[2].find(':')+2:audioInfo[2].rfind(' ')]

		# Проверка наличия результатов работы команды
		if not duration or not bitrate:
			attempts += 1
			logger.error(f"Отсутствует длительность аудио или его битрейт: ({attempts}):\n\tДлительность: {duration}\n\tБитрейт: {bitrate}")
			self.url = ""
			time.sleep(settings_conf.TIME_ATTEMPT)
			self._getAudioInfo(origin_url, attempts)
		# Выход из рекурсии, если информация была успешно получена
		return duration, bitrate

	def _getAudioUrl(self, cmd: str, attempts = 0) -> str:
		"""Получение прямой ссылки аудио.

		Args:
			cmd (str): Команда для прямой ссылки аудио.
			attempts (int, optional): Количество попыток неуспешного выполнения команды. Defaults to 0.

		Raises:
			CustomError: Вызов ошибки с настраиваемым содержанием.

		Returns:
			str: Прямая ссылка аудио.
		"""
		# Выход из рекурсии, если пользователь отменил выполнение запроса
		if self._stop:
			raise CustomError(code=CustomErrorCode.STOP_THREAD)
		# Выход из рекурсии, если превышено число попыток выполнения команды
		if attempts == settings_conf.MAX_ATTEMPTS:
			raise CustomError("Ошибка: Невозможно получить информацию о видео.")
		proc = subprocess.Popen(cmd, stdout = subprocess.PIPE, stderr = subprocess.PIPE, text = True, shell = True)
		stdout, stderr = proc.communicate()
		if stderr:
			logger.error(f'Ошибка получения прямой ссылки ({attempts}): {stderr.strip()}')
			# Данная ошибка может произойти неожиданно, поэтому приходится повторять попытку выполнения команды через определённое время
			if ('http error 403' in stderr.lower()):
				attempts += 1
				time.sleep(settings_conf.TIME_ATTEMPT)
				self._getAudioUrl(cmd, attempts)
			elif ('sign in to confirm your age' in stderr.lower()):
				raise CustomError('Ошибка: Невозможно скачать видео из-за возрастных ограничений.')
			elif ('video unavailable' in stderr.lower()):
				raise CustomError('Ошибка: Видео недоступно из-за авторских прав или по другим причинам.')
			else:
				raise CustomError('Ошибка: Некорректный адрес источника.')

		# Проверка наличия результатов работы команды
		if not stdout:
			attempts += 1
			logger.error(f"Прямая ссылка нулевая: ({attempts}): {stdout}")
			time.sleep(settings_conf.TIME_ATTEMPT)
			self._getAudioUrl(cmd, attempts)
		# Выход из рекурсии, если информация была успешно получена
		return stdout.strip()

	def _downloadAudio(self, cmd_body: str, origin_url: str, attempts = 0):
		"""Загрузка аудио.

		Args:
			cmd (str): Команда для загрузки аудио.
			attempts (int, optional): Количество попыток неуспешного выполнения команды. Defaults to 0.

		Raises:
			CustomError: Вызов ошибки с настраиваемым содержанием.
		"""
		# Выход из рекурсии, если превышено число попыток выполнения команды
		if attempts == settings_conf.MAX_ATTEMPTS:
			raise CustomError("Ошибка: Невозможно загрузить видео.")
		if not self.url:
			# Получение прямой ссылки аудио
			self.url = self._getAudioUrl(cmdAudioUrl(origin_url))

		# Загрузка файла
		last_msg_time = time.time()
		cmd = cmd_body + '-i "{0}" {1}'.format(self.url, self.path)
		proc = subprocess.Popen(cmd, stderr = subprocess.PIPE, text = True, shell = True)
		line = str(proc.stderr.readline())
		# Отправка сообщения с началом загрузки аудио
		if line and not attempts:
			if self._playlist:
				self.progress_msg_id = sayOrReply(self.user_id, f'Загрузка началась [{self.task_id}/{self.task_size}]')
			else:
				self.progress_msg_id = sayOrReply(self.user_id, 'Загрузка началась', self.msg_id)
		while line:
			# Выход из рекурсии, если пользователь отменил выполнение запроса
			if self._stop:
				raise CustomError(code=CustomErrorCode.STOP_THREAD)
			if "size=" in line.lower():
				# Обновление сообщения с процессом загрузки по количеству прошедших "тактов" (необходимо для предотвращения непреднамеренного спама)
				if round(time.time() - last_msg_time) >= settings_conf.MSG_PERIOD:
					size = line[6:].strip()
					size = int(size[:size.find(' ')-2])
					if size:
						vars.vk_bot.messages.edit(peer_id = self.user_id, message = f"Загружено {int(round(size * 1024 / self.file_size, 2) * 100)}% ({round(size / 1024, 2)} / {round(self.file_size / 1024**2, 2)} Мб)", message_id = self.progress_msg_id)
					last_msg_time = time.time()
			elif "out of range" in line.lower():
				raise CustomError("Ошибка: Время среза превышает продолжительность аудио.")
			else:
				logger.warning(f'Возникла ошибка во время скачивания файла ({attempts}):\n\t{line}')
				attempts += 1
				self.url = ""
				time.sleep(settings_conf.TIME_ATTEMPT)
				self._downloadAudio(cmd_body, origin_url, attempts)

			line = str(proc.stderr.readline())

		msg = "Загрузка файла завершена. Началась обработка"
		if self._playlist:
			msg += f" [{self.task_id}/{self.task_size}]"
		vars.vk_bot.messages.edit(peer_id = self.user_id, message = msg, message_id = self.progress_msg_id)
		logger.debug(f'Скачивание видео завершено, попытки: {attempts}')

	def run(self):
		"""Запуск воркера в отдельном потоке.

		Raises:
			CustomError: Вызов ошибки с настраиваемым содержанием.
		"""
		logger.info('AudioWorker: Запуск.')
		try:
			task = self._task

			if (len(task) == 3):
				self._playlist = True
				self.task_id   = task[2][0]
				self.task_size = task[2][1]
			options = task[1]

			param                = task[0]
			self.msg_start_id    = param[0] # id сообщения с размером очереди (необходимо для удаления в конце обработки запроса)
			self.user_id         = param[1] # id пользователя
			self.msg_id          = param[2] # id сообщения пользователя (необходимо для ответа на него)
			self.path            = ""       # Путь сохранения файла
			self.progress_msg_id = 0        # id сообщения с прогрессом загрузки
			self.url             = "" 		# Прямая ссылка аудио

			downloadString = 'ffmpeg -y -hide_banner -loglevel error -stats '

			logger.debug(f'Получена задача: {task}')
			# Получение продолжительности и битрейта аудио для расчёта приблизительного веса файла
			audioInfo = self._getAudioInfo(options[0])
			logger.debug(f"Информация об аудио успешно получена: {audioInfo}")
			audioDuration = self._toSeconds(audioInfo[0])
			if audioDuration == -1:
				raise CustomError("Ошибка: Невозможно получить информацию о видео.")
			# Обработка времени среза, в случае если оно указано
			if len(options) > 3:
				startTime = self._toSeconds(options[3])
				if startTime == -1:
					raise CustomError('Ошибка: Неверный формат времени среза.')
				audioDuration = audioDuration - startTime
				if len(options) == 5:
					endTime = self._toSeconds(options[4])
					if endTime < audioDuration + startTime:
						audioDuration = endTime - startTime
				downloadString += f'-ss {startTime} -t {audioDuration} '

			if audioDuration <= 0:
				raise CustomError("Ошибка: Время среза превышает продолжительность аудио.")
			# Приблизительный вес файла
			self.file_size = audioDuration * int(audioInfo[1]) * 128 #  F (bytes) = t (s) * bitrate (kb / s) * 1024 // 8

			# Проверка размера файла (необходимо из-за внутренних ограничений VK)
			logger.debug(f"Предварительный размер файла: {round(self.file_size / 1024**2, 2)} Mb")
			if self.file_size * 0.9 > settings_conf.MAX_FILESIZE:
				raise CustomError('Ошибка: Размер аудиозаписи превышает 200 Мб!')

			# Получение id аудио для отслеживания текущих загрузок (в будущем будет интегрирована ДБ для оптимизации работы при одинаковых запросах)
			proc = subprocess.Popen(cmdVideoInfo('id', options[0]), stdout = subprocess.PIPE, text = True, shell = True)
			self.path = proc.communicate()[0].strip()

			# Проверка наличия пути и url источника
			if not self.path:
				raise CustomError('Ошибка: Некорректный адрес источника.')
			# Добавление в конец id штампа времени для уникальности названия файлов (временное решение во время отсутствия ДБ)
			now = str(time.time())
			now = now[now.find('.')-2:now.find('.')] + now[now.find('.')+1:now.find('.')+3]
			self.path += f"{now}.mp3"

			# Скачивание аудио
			self._downloadAudio(downloadString, options[0])
			# Получение реального размера файла
			self.file_size = os.path.getsize(self.path)
			# Проверка размера файла (необходимо из-за внутренних ограничений VK)
			logger.debug(f"Фактический размер файла: {round(self.file_size / 1024**2, 2)} Mb")
			if self.file_size > settings_conf.MAX_FILESIZE:
				raise CustomError('Размер аудиозаписи превышает 200 Мб!')
			else:
				# Поиск и коррекция данных аудиозаписи
				artist = 'unknown'
				self.title = 'unknown'
				# URL
				if len(options) == 1:
					proc = subprocess.Popen(cmdVideoInfo('title', options[0]), stdout = subprocess.PIPE, text = True, shell = True)
					file_name = proc.communicate()[0].strip()
					if file_name:
						self.title = file_name
					proc = subprocess.Popen(cmdVideoInfo('channel', options[0]), stdout = subprocess.PIPE, text = True, shell = True)
					file_author = proc.communicate()[0].strip()
					if file_author:
						artist = file_author
				# URL + song_name
				elif len(options) == 2:
					self.title = options[1]
					proc = subprocess.Popen(cmdVideoInfo('channel', options[0]), stdout = subprocess.PIPE, text = True, shell = True)
					file_author = proc.communicate()[0].strip()
					if file_author:
						artist = file_author
				# URL + song_name + song_author
				else:
					artist = options[2]
					self.title = options[1]
				if len(self.title) > 50:
					self.title[0:51]
				# Остановка загрузки аудио в Вк, если пользователь отменил выполнение запроса
				if self._stop:
					raise CustomError(code=CustomErrorCode.STOP_THREAD)
				# Загрузка аудиозаписи на сервера VK + её отправка получателю
				audio_obj = vars.vk_agent_upload.audio(self.path, artist, self.title)
				audio_id = audio_obj.get('id')
				audio_owner_id = audio_obj.get('owner_id')
				attachment = f'audio{audio_owner_id}_{audio_id}'

				if self._playlist:
					vars.vk_bot.messages.send(peer_id = self.user_id, attachment = attachment, random_id = get_random_id())
					# Обновление статуса компонента плейлиста в отчёте
					vars.audioTools.playlist_result[self.user_id][self.title] = playlist_conf.PLAYLIST_SUCCESSFUL
				else:
					vars.vk_bot.messages.send(peer_id = self.user_id, attachment = attachment, reply_to = self.msg_id, random_id = get_random_id())

		except CustomError as er:
			# Обработка ошибок, не относящихся к преднамеренной остановке потока
			if er.code != CustomErrorCode.STOP_THREAD:
				if not self._playlist:
					sayOrReply(self.user_id, er, self.msg_id)
				logger.error(f'Custom: {er}')

		except vk_api.exceptions.ApiError as er:
			if self._playlist:
				# Ошибка авторских прав
				if er.code == 270 and self.title:
					vars.audioTools.playlist_result[self.user_id][self.title] = playlist_conf.PLAYLIST_COPYRIGHT
			else:
				error_string = 'Ошибка: Невозможно обработать запрос. Убедитесь, что запрос корректный, и отправьте его повторно.'
				# Ошибка авторских прав
				if er.code == 270:
					error_string = 'Ошибка: Правообладатель ограничил доступ к данной аудиозаписи. Загрузка прервана'
				elif er.code == 15:
					if self.file_size < 50 * 1024:
						error_string = 'Ошибка: Вк запрещает загрузку треков, вес которых меньше 50 Кб.'
				sayOrReply(self.user_id, f'{error_string}', self.msg_id)
			# Добавить проверку через sql на успешность загрузки видео
			logger.error(f'VK API: \n\tCode: {er.code}\n\tBody: {er}')

		except Exception as er:
			# Обработка ошибок, не относящихся к компонентам плейлиста
			if not self._playlist:
				error_string = 'Ошибка: Невозможно обработать запрос. Убедитесь, что запрос корректный, и отправьте его повторно.'
				sayOrReply(self.user_id, error_string, self.msg_id)
			logger.error(f'Исключение: {er}')

		finally:
			# Удаление сообщения с прогрессом
			if self.progress_msg_id:
				vars.vk_bot.messages.delete(delete_for_all = 1, message_ids = self.progress_msg_id)

			# Удаление загруженного файла
			if os.path.isfile(self.path):
				os.remove(self.path)
				logger.debug(f'Успешно удалил аудио-файл: {self.path}')
			else:
				logger.error('Ошибка: Аудио-файл не существует.')

			if not self._stop:
				# Удаление сообщения с порядком очереди
				if(vars.userRequests[self.user_id] < 0):
					vars.userRequests[self.user_id] += 1
					if (vars.userRequests[self.user_id] == -1):
						vars.userRequests[self.user_id] = 0
						vars.vk_bot.messages.delete(delete_for_all = 1, message_ids = self.msg_start_id)
						vars.audioTools.playlist_summarize(self.user_id)
				else:
					vars.userRequests[self.user_id] -= 1
					vars.vk_bot.messages.delete(delete_for_all = 1, message_ids = self.msg_start_id)
				# Отчёт о проделанной обратки
				logger.debug(
					(
						'Завершено:\n'+
						'\tЗадача: {0}\n' +
						'\tПуть: {1}\n' +
						'\tОчередь текущего пользователя ({2}): {3}\n' +
						'\tОчередь текущего worker\'а: {4}'
					).format(
						self._task,
						self.path,
						self.user_id,
						vars.userRequests[self.user_id],
						vars.queueHandler.size_queue
					)
				)
				# Очистка памяти, в случае пустой переменной
				if not vars.userRequests[self.user_id]: del vars.userRequests[self.user_id]
				# Подтверждение выполненной задачи потоком
				vars.queueHandler.ack_request(self.user_id, threading.current_thread())
			else:
				# Отчёт о проделанной обратки
				logger.debug(
					(
						'Завершено:\n'+
						'\tЗадача: {0}\n' +
						'\tПуть: {1}\n' +
						'\tОчередь текущего пользователя ({2}): null\n' +
						'\tОчередь текущего worker\'а: null'
					).format(
						self._task,
						self.path,
						self.user_id
					)
				)

	def stop(self):
		"""Вынужденная остановка воркера.
		"""
		self._stop = True
