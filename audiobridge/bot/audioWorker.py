#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import os
import threading, subprocess
import time

import vk_api
from vk_api.utils import get_random_id

from audiobridge.tools.customErrors import CustomError

from audiobridge.common.config import Settings, PlaylistStates
from audiobridge.common import vars
from audiobridge.tools.sayOrReply import sayOrReply


logger = logging.getLogger('logger')
settings_conf = Settings()
playlist_conf = PlaylistStates()

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

	def tryCmd(self, command) -> tuple:
		status = (False, "Ошибка: Неизвестная. Обратитесь к разработчикам для выявления причины ошибки.")
		attempts = 0
		try:
			while attempts != settings_conf.MAX_ATTEMPTS:
				if self._stop:
					return (False, "")
				proc = subprocess.Popen(command, stdout = subprocess.PIPE, stderr = subprocess.PIPE, text = True, shell = True)
				stdout, stderr = proc.communicate()
				if (stderr):
					logger.error(f'Ошибка выполнения команды ({attempts}): {stderr.strip()}')
					if ('HTTP Error 403' in stderr):
						attempts += 1
						time.sleep(settings_conf.TIME_ATTEMPT)
						continue
					elif ('Sign in to confirm your age' in stderr):
						raise CustomError('Ошибка: Невозможно скачать видео из-за возрастных ограничений.')
					elif ('Video unavailable' in stderr):
						raise CustomError('Ошибка: Видео недоступно из-за авторских прав или по другим причинам.')
					else:
						raise CustomError('Ошибка: Некорректный адрес источника.')
				if stdout:
					status = (True, stdout)
					break

		except CustomError as er:
			return (False, er)

		except Exception as er:
			logger.error(f'Исключение: {er}')
			return (False, "Ошибка: Невозможно обработать запрос. Убедитесь, что запрос корректный, и отправьте его повторно.")

		finally:
			return status

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
			self.path            = ''       # Путь сохранения файла
			self.progress_msg_id = 0        # id сообщения с прогрессом загрузки

			downloadString = 'youtube-dl --no-warnings --no-part --newline --id --extract-audio --audio-format mp3 --max-downloads 1 "{0}"'.format(options[0])
			cUpdateProcess = -1

			logger.debug(f'Получена задача: {task}')

			result = self.tryCmd(vars.audioTools.getVideoInfo('duration', options[0]))
			if not result[0]:
				raise CustomError([1])
			video_duration = vars.audioTools.getSeconds(result)
			if video_duration == -1:
				raise CustomError("Ошибка: неизвестная. Обратитесь к разработчикам для выявления проблем.")
			logger.debug(f'Получена длительность оригинального видео (в сек.): {video_duration}')

			# Обработка запроса с таймингами среза
			audioDuration = 0
			if len(options) > 3:
				startTime = vars.audioTools.getSeconds(options[3])
				if startTime == -1:
					raise CustomError('Ошибка: Неверный формат времени среза.')
				audioDuration = video_duration - startTime
				if len(options) == 5:
					audioDuration = vars.audioTools.getSeconds(options[4]) - startTime

			if video_duration > settings_conf.MAX_VIDEO_DURATION and audioDuration > settings_conf.MAX_VIDEO_DURATION:
				raise CustomError('Ошибка: Длительность будущей аудиозаписи превышает 3 часа.')
			if audioDuration >= video_duration or audioDuration <= 0:
				audioDuration = 0

			result = self.tryCmd(vars.audioTools.getVideoInfo('id', options[0]))
			if not result[0]:
				raise CustomError([1])
			self.path = result.strip()

			result = self.tryCmd(vars.audioTools.getAudioUrl(options[0]))
			if not result[0]:
				raise CustomError([1])
			url = result.strip()

			# Проверка наличия пути и url источника
			if not self.path or not url:
				raise CustomError('Ошибка: Некорректный адрес источника.')
#--------------------------finish----------------------------------------------------
			# Загрузка файла
			attempts = 0
			while attempts != settings_conf.MAX_ATTEMPTS:
				proc = subprocess.Popen(downloadString, stdout = subprocess.PIPE, stderr = subprocess.PIPE, text = True, shell = True)
				line = str(proc.stdout.readline())
				while line:
					if self._stop: return

					# Поиск пути сохранения файла
					if 'Destination' in line and '.mp3' in line:
						self.path = line[line.find(':')+2:len(line)].strip()
						logger.debug(f'Путь: {self.path}')

					# Обновление сообщения с процессом загрузки файла
					if ' of ' in line:
						if cUpdateProcess == -1:
							if self._playlist:
								self.progress_msg_id = sayOrReply(self.user_id, f'Загрузка началась [{self.task_id}/{self.task_size}]')
							else:
								self.progress_msg_id = sayOrReply(self.user_id, 'Загрузка началась', self.msg_id)
						if cUpdateProcess == settings_conf.MSG_PERIOD:
							progress = line[line.find(' '):line.find('КиБ/сек.') + 5].strip()
							if progress:
								vars.vk_bot.messages.edit(peer_id = self.user_id, message = progress, message_id = self.progress_msg_id)
							cUpdateProcess = 0
						if ' in ' in line:
							progress = line[line.find(' '):len(line)].strip()
							if progress:
								msg = progress
								if self._playlist: msg += f' [{self.task_id}/{self.task_size}]'
								vars.vk_bot.messages.edit(peer_id = self.user_id, message = msg, message_id = self.progress_msg_id)
						cUpdateProcess += 1
					line = str(proc.stdout.readline())
				stdout, stderr = proc.communicate()

				if (stderr):
					if ('HTTP Error 403' in stderr): # ERROR: unable to download video data: HTTP Error 403: Forbidden
						logger.warning(f'Поймал ошибку 403.')
						attempts += 1
						time.sleep(settings_conf.TIME_ATTEMPT)
						continue
					else:
						logger.error(f'Скачивание видео ({attempts}): {stderr.strip()}')
						raise CustomError('Невозможно скачать видео!')
				else:
					break
			logger.debug(f'Скачивание видео, попытки: {attempts}')
#------------------------------------------------------------------------------------
			# Проверка размера файла (необходимо из-за внутренних ограничений VK)
			if os.path.getsize(self.path) > settings_conf.MAX_FILESIZE:
				raise CustomError('Размер аудиозаписи превышает 200 Мб!')
			else:
				# Поиск и коррекция данных аудиозаписи
				artist = 'unknown'
				self.title = 'unknown'

				# URL
				if len(options) == 1:
					proc = subprocess.Popen(vars.audioTools.getVideoInfo('title', options[0]), stdout = subprocess.PIPE, text = True, shell = True)
					file_name = proc.communicate()[0].strip()
					if file_name:
						self.title = file_name
					proc = subprocess.Popen(vars.audioTools.getVideoInfo('channel', options[0]), stdout = subprocess.PIPE, text = True, shell = True)
					file_author = proc.communicate()[0].strip()
					if file_author:
						artist = file_author

				# URL + song_name
				elif len(options) == 2:
					self.title = options[1]
					proc = subprocess.Popen(vars.audioTools.getVideoInfo('channel', options[0]), stdout = subprocess.PIPE, text = True, shell = True)
					file_author = proc.communicate()[0].strip()
					if file_author:
						artist = file_author

				# URL + song_name + song_autor
				else:
					artist = options[2]
					self.title = options[1]
				if len(self.title) > 50:
					self.title[0:51]

				if self._stop: return
				# Загрузка аудиозаписи на сервера VK + её отправка получателю
				audio_obj = vars.vk_bot.audio(self.path, artist, self.title)
				audio_id = audio_obj.get('id')
				audio_owner_id = audio_obj.get('owner_id')
				attachment = f'audio{audio_owner_id}_{audio_id}'

				if self._playlist:
					vars.vk_bot.messages.send(peer_id = self.user_id, attachment = attachment, random_id = get_random_id())
					vars.audioTools.playlist_result[self.user_id][self.title] = playlist_conf.PLAYLIST_SUCCESSFUL
				else:
					vars.vk_bot.messages.send(peer_id = self.user_id, attachment = attachment, reply_to = self.msg_id, random_id = get_random_id())

		except CustomError as er:
			if er:
				if not self._playlist:
					sayOrReply(self.user_id, er, self.msg_id)
				logger.error(f'Custom: {er}')

		except vk_api.exceptions.ApiError as er:
			if self._playlist:
				if er.code == 270 and self.title:
					vars.audioTools.playlist_result[self.user_id][self.title] = playlist_conf.PLAYLIST_COPYRIGHT
			else:
				error_string = 'Ошибка: Невозможно обработать запрос. Убедитесь, что запрос корректный, и отправьте его повторно.'
				if er.code == 270:
					error_string = 'Правообладатель ограничил доступ к данной аудиозаписи. Загрузка прервана'
				sayOrReply(self.user_id, f'Ошибка: {error_string}', self.msg_id)
			# Добавить проверку через sql на успешность загрузки видео
			logger.error(f'VK API: {er}')

		except Exception as er:
			if not self._playlist:
				error_string = 'Ошибка: Невозможно обработать запрос. Убедитесь, что запрос корректный, и отправьте его повторно.'
				sayOrReply(self.user_id, error_string, self.msg_id)
			logger.error(f'Исключение: {er}')

		finally:
			# Удаление сообщения с прогрессом
			if self.progress_msg_id:
				vars.vk_bot.messages.delete(delete_for_all = 1, message_ids = self.progress_msg_id)

			# Удаление загруженного файла
			if self.path:
				if not '.mp3' in self.path:
					for f_name in os.listdir():
						if f_name.startswith(self.path): self.path = f_name

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
				if not vars.userRequests[self.user_id]: del vars.userRequests[self.user_id]
				vars.queueHandler.ack_request(self.user_id, threading.current_thread())
			else:
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
