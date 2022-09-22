#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import os
import threading, subprocess
import time

import vk_api
from vk_api.utils import get_random_id

from audiobridge.bot.customErrors import CustomError

from audiobridge.common.config import Settings, PlaylistStates
from audiobridge.common import constants as const
from audiobridge.common.sayOrReply import sayOrReply


logger = logging.getLogger('logger')

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

			attempts = 0
			video_duration = -1
			while attempts != Settings.MAX_ATTEMPTS:
				# Проверка на соблюдение ограничения длительности видео (MAX_VIDEO_DURATION)
				proc = subprocess.Popen(const.audioTools.getVideoInfo('duration', options[0]), stdout = subprocess.PIPE, stderr = subprocess.PIPE, text = True, shell = True)
				stdout, stderr = proc.communicate()
				if (stderr):
					logger.error(f'Получение длительности видео ({attempts}): {stderr.strip()}')
					if ('HTTP Error 403' in stderr):
						attempts += 1
						time.sleep(Settings.TIME_ATTEMPT)
						continue
					elif ('Sign in to confirm your age' in stderr):
						raise CustomError('Ошибка: Невозможно скачать видео из-за возрастных ограничений.')
					elif ('Video unavailable' in stderr):
						raise CustomError('Ошибка: Видео недоступно из-за авторских прав или по другим причинам.')
					else:
						raise CustomError('Ошибка: Некорректный адрес Youtube-видео.')
				video_duration = const.audioTools.getSeconds(stdout)
				if video_duration != -1:
					break
			logger.debug(f'Получение длительности видео (в сек.), попытки: {attempts}')

			if video_duration == -1:
				raise CustomError('Ошибка: Возникла неизвестная ошибка, обратитесь к разработчику...')
			elif video_duration > Settings.MAX_VIDEO_DURATION:
				raise CustomError('Ошибка: Длительность будущей аудиозаписи превышает 3 часа.')

			# Обработка запроса с таймингами среза
			if len(options) > 3:
				startTime = const.audioTools.getSeconds(options[3])
				if startTime == -1:
					raise CustomError('Ошибка: Неверный формат времени среза.')
				audioDuration = video_duration - startTime
				if len(options) == 5:
					audioDuration = const.audioTools.getSeconds(options[4]) - startTime

			proc = subprocess.Popen(const.audioTools.getVideoInfo('id', options[0]), stdout = subprocess.PIPE, text = True, shell = True)
			self.path = proc.communicate()[0].strip()

			# Загрузка файла
			attempts = 0
			while attempts != Settings.MAX_ATTEMPTS:
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
						if cUpdateProcess == Settings.MSG_PERIOD:
							progress = line[line.find(' '):line.find('КиБ/сек.') + 5].strip()
							if progress:
								const.vk_bot.messages.edit(peer_id = self.user_id, message = progress, message_id = self.progress_msg_id)
							cUpdateProcess = 0
						if ' in ' in line:
							progress = line[line.find(' '):len(line)].strip()
							if progress:
								msg = progress
								if self._playlist: msg += f' [{self.task_id}/{self.task_size}]'
								const.vk_bot.messages.edit(peer_id = self.user_id, message = msg, message_id = self.progress_msg_id)
						cUpdateProcess += 1
					line = str(proc.stdout.readline())
				stdout, stderr = proc.communicate()

				if (stderr):
					if ('HTTP Error 403' in stderr): # ERROR: unable to download video data: HTTP Error 403: Forbidden
						logger.warning(f'Поймал ошибку 403.')
						attempts += 1
						time.sleep(Settings.TIME_ATTEMPT)
						continue
					else:
						logger.error(f'Скачивание видео ({attempts}): {stderr.strip()}')
						raise CustomError('Невозможно скачать видео!')
				else:
					break
			logger.debug(f'Скачивание видео, попытки: {attempts}')

			# Проверка валидности пути сохранения файла
			if not self.path:
				logger.error(f'Путь: попытки: {attempts}')
				raise CustomError('Ошибка: Некорректный адрес Youtube-видео.')

			# Проверка размера файла (необходимо из-за внутренних ограничений VK)
			if os.path.getsize(self.path) > Settings.MAX_FILESIZE:
				raise CustomError('Размер аудиозаписи превышает 200 Мб!')
			else:
				os.rename(self.path, 'B' + self.path)
				self.path = 'B' + self.path

				if self._stop: return

				# Создание аудиосегмента
				if len(options) > 3 and audioDuration < video_duration:
					baseAudio = self.path
					self.path = 'A' + self.path
					audioString = 'ffmpeg -ss {0} -t {1} -i {2} {3}'.format(startTime, audioDuration, baseAudio, self.path)
					logger.debug(f'Параметры запуска ffmpeg: {audioString}')
					subprocess.Popen(audioString, stdout = subprocess.PIPE, text = True, shell = True).wait()
					if os.path.isfile(baseAudio):
						os.remove(baseAudio)
						logger.debug(f'Успех: Удаление файла видео: "{baseAudio}".')
					else:
						logger.error(f'Ошибка: Файл видео не существует.')

				# Поиск и коррекция данных аудиозаписи
				artist = 'unknown'
				self.title = 'unknown'

				# URL
				if len(options) == 1:
					proc = subprocess.Popen(const.audioTools.getVideoInfo('title', options[0]), stdout = subprocess.PIPE, text = True, shell = True)
					file_name = proc.communicate()[0].strip()
					if file_name:
						self.title = file_name
					proc = subprocess.Popen(const.audioTools.getVideoInfo('channel', options[0]), stdout = subprocess.PIPE, text = True, shell = True)
					file_author = proc.communicate()[0].strip()
					if file_author:
						artist = file_author

				# URL + song_name
				elif len(options) == 2:
					self.title = options[1]
					proc = subprocess.Popen(const.audioTools.getVideoInfo('channel', options[0]), stdout = subprocess.PIPE, text = True, shell = True)
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
				audio_obj = const.vk_agent_upload.audio(self.path, artist, self.title)
				audio_id = audio_obj.get('id')
				audio_owner_id = audio_obj.get('owner_id')
				attachment = f'audio{audio_owner_id}_{audio_id}'

				if self._playlist:
					const.vk_bot.messages.send(peer_id = self.user_id, attachment = attachment, random_id = get_random_id())
					const.audioTools.playlist_result[self.user_id][self.title] = PlaylistStates.PLAYLIST_SUCCESSFUL
				else:
					const.vk_bot.messages.send(peer_id = self.user_id, attachment = attachment, reply_to = self.msg_id, random_id = get_random_id())

		except CustomError as er:
			if not self._playlist:
				sayOrReply(self.user_id, er, self.msg_id)
			logger.error(f'Custom: {er}')

		except vk_api.exceptions.ApiError as er:
			if self._playlist:
				if er.code == 270 and self.title:
					const.audioTools.playlist_result[self.user_id][self.title] = PlaylistStates.PLAYLIST_COPYRIGHT
			else:
				error_string = 'Ошибка: Невозможно обработать плейлист. Убедитесь, что запрос корректный и отправьте его повторно.'
				if er.code == 270:
					error_string = 'Правообладатель ограничил доступ к данной аудиозаписи. Загрузка прервана'
				sayOrReply(self.user_id, f'Ошибка: {error_string}', self.msg_id)
			# Добавить проверку через sql на успешность загрузки видео
			logger.error(f'VK API: {er}')

		except Exception as er:
			if not self._playlist:
				error_string = 'Ошибка: Невозможно обработать плейлист. Убедитесь, что запрос корректный и отправьте его повторно.'
				sayOrReply(self.user_id, error_string, self.msg_id)
			logger.error(f'Исключение: {er}')

		finally:
			# Удаление сообщения с прогрессом
			if self.progress_msg_id:
				const.vk_bot.messages.delete(delete_for_all = 1, message_ids = self.progress_msg_id)

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
				if(const.userRequests[self.user_id] < 0):
					const.userRequests[self.user_id] += 1
					if (const.userRequests[self.user_id] == -1):
						const.userRequests[self.user_id] = 0
						const.vk_bot.messages.delete(delete_for_all = 1, message_ids = self.msg_start_id)
						const.audioTools.playlist_summarize(self.user_id)
				else:
					const.userRequests[self.user_id] -= 1
					const.vk_bot.messages.delete(delete_for_all = 1, message_ids = self.msg_start_id)

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
						const.userRequests[self.user_id],
						const.queueHandler.size_queue
					)
				)
				if not const.userRequests[self.user_id]: del const.userRequests[self.user_id]
				const.queueHandler.ack_request(self.user_id, threading.current_thread())
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
