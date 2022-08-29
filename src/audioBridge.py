#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, sys, time, locale, json, logging, threading, subprocess
from sys import platform
from datetime import datetime, date # работа с датой и временем

import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.utils import get_random_id

import db.database as database
import loggerSetup
from commands.user import *
from config import *
from customErrors import *


class MyVkBotLongPoll(VkBotLongPoll):
	"""Класс обработки событий от VkLongPoll.

	Args:
		VkBotLongPoll (VkLongPoll): интерфейс управления VK
	"""
	def listen(self):
		while True:
			try:
				for event in self.check():
					yield event
			except Exception as e:
				logger.error(e)

# Функция отправки сообщения
def sayOrReply(user_id: int, _message: str, _reply_to: int = None) -> int:
	if _reply_to:
		return vk_bot.messages.send(peer_id = user_id, message = _message, reply_to = _reply_to, random_id = get_random_id())
	return vk_bot.messages.send(peer_id = user_id, message = _message, random_id = get_random_id())


class AudioTools():
	"""Класс вспомогательных функций для выполнения запроса."""

	def __init__(self):
		self.playlist_result = {}

	# Работа со строкой времени; в скором времени избавимся от этой функции
	def getSeconds(self, strTime):
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

	# Получить информацию о видео по ключу
	def getVideoInfo(self, key, url):
		return 'youtube-dl --max-downloads 1 --no-warnings --get-filename -o "%({0})s" {1}'.format(key, url)

	# Получить информацию о плейлисте
	def getPlaylistInfo(self, filter, url):
		return 'youtube-dl --no-warnings --dump-json --newline {0} {1}'.format(filter, url)

	# Обработка плейлиста
	def playlist_processing(self, task):
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

			vk_bot.messages.edit(peer_id = user_id, message = f'Запрос добавлен в очередь (плейлист: {len(urls)})', message_id = msg_start_id)

		except CustomError as er:
			sayOrReply(user_id, f'Произошла ошибка: {er}', msg_id)

			# Удаление сообщения с порядком очереди
			vk_bot.messages.delete(delete_for_all = 1, message_ids = msg_start_id)
			del userRequests[user_id]
			logger.error(f'Произошла ошибка: {er}')

		except Exception as er:
			error_string = 'Ошибка: Невозможно обработать плейлист. Убедитесь, что запрос корректный и отправьте его повторно.'
			sayOrReply(user_id, error_string, msg_id)

			# Удаление сообщения с порядком очереди
			vk_bot.messages.delete(delete_for_all = 1, message_ids = msg_start_id)
			del userRequests[user_id]
			logger.error(f'Поймал исключение: {er}')

		else:
			self.playlist_result[user_id] = {'msg_id' : msg_id}  # Отчёт скачивания плейлиста
			for i, url in enumerate(urls):
				self.playlist_result[user_id][url[1]] = PlaylistStates.PLAYLIST_UNSTATED
				userRequests[user_id] -= 1
				queueHandler.add_new_request([param, [url[0]], [i+1, len(urls)]])

	# Подвести итог
	def playlist_summarize(self, user_id):
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


class AudioWorker(threading.Thread):
	"""Класс скачивания песен и загрузки в ВК."""

	def __init__(self, task: list):
		super(AudioWorker, self).__init__()
		self._stop     = False
		self._task     = task
		self._playlist = False

	def run(self):
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

			if options[0][0] == '-':
				logger.warning('Меня попытались крашнуть!')
				raise CustomError('Ошибка: Некорректный адрес Youtube-видео.')

			downloadString = 'youtube-dl --no-warnings --no-part --newline --id --extract-audio --audio-format mp3 --max-downloads 1 "{0}"'.format(options[0])
			cUpdateProcess = -1

			logger.debug(f'Получена задача: {task}')

			attempts = 0
			video_duration = -1
			while attempts != Settings.MAX_ATTEMPTS:
				# Проверка на соблюдение ограничения длительности видео (MAX_VIDEO_DURATION)
				proc = subprocess.Popen(audioTools.getVideoInfo('duration', options[0]), stdout = subprocess.PIPE, stderr = subprocess.PIPE, text = True, shell = True)
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
				video_duration = audioTools.getSeconds(stdout)
				if video_duration != -1:
					break
			logger.debug(f'Получение длительности видео (в сек.), попытки: {attempts}')

			if video_duration == -1:
				raise CustomError('Ошибка: Возникла неизвестная ошибка, обратитесь к разработчику...')
			elif video_duration > Settings.MAX_VIDEO_DURATION:
				raise CustomError('Ошибка: Длительность будущей аудиозаписи превышает 3 часа.')

			# Обработка запроса с таймингами среза
			if len(options) > 3:
				startTime = audioTools.getSeconds(options[3])
				if startTime == -1:
					raise CustomError('Ошибка: Неверный формат времени среза.')
				audioDuration = video_duration - startTime
				if len(options) == 5:
					audioDuration = audioTools.getSeconds(options[4]) - startTime

			proc = subprocess.Popen(audioTools.getVideoInfo('id', options[0]), stdout = subprocess.PIPE, text = True, shell = True)
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
								vk_bot.messages.edit(peer_id = self.user_id, message = progress, message_id = self.progress_msg_id)
							cUpdateProcess = 0
						if ' in ' in line:
							progress = line[line.find(' '):len(line)].strip()
							if progress:
								msg = progress
								if self._playlist: msg += f' [{self.task_id}/{self.task_size}]'
								vk_bot.messages.edit(peer_id = self.user_id, message = msg, message_id = self.progress_msg_id)
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
					proc = subprocess.Popen(audioTools.getVideoInfo('title', options[0]), stdout = subprocess.PIPE, text = True, shell = True)
					file_name = proc.communicate()[0].strip()
					if file_name:
						self.title = file_name
					proc = subprocess.Popen(audioTools.getVideoInfo('channel', options[0]), stdout = subprocess.PIPE, text = True, shell = True)
					file_author = proc.communicate()[0].strip()
					if file_author:
						artist = file_author

				# URL + song_name
				elif len(options) == 2:
					self.title = options[1]
					proc = subprocess.Popen(audioTools.getVideoInfo('channel', options[0]), stdout = subprocess.PIPE, text = True, shell = True)
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
				audio_obj = vk_agent_upload.audio(self.path, artist, self.title)
				audio_id = audio_obj.get('id')
				audio_owner_id = audio_obj.get('owner_id')
				attachment = f'audio{audio_owner_id}_{audio_id}'

				if self._playlist:
					vk_bot.messages.send(peer_id = self.user_id, attachment = attachment, random_id = get_random_id())
					audioTools.playlist_result[self.user_id][self.title] = PlaylistStates.PLAYLIST_SUCCESSFUL
				else:
					vk_bot.messages.send(peer_id = self.user_id, attachment = attachment, reply_to = self.msg_id, random_id = get_random_id())

		except CustomError as er:
			if not self._playlist:
				sayOrReply(self.user_id, er, self.msg_id)
			logger.error(f'Custom: {er}')

		except vk_api.exceptions.ApiError as er:
			if self._playlist:
				if er.code == 270 and self.title:
					audioTools.playlist_result[self.user_id][self.title] = PlaylistStates.PLAYLIST_COPYRIGHT
			else:
				error_string = 'Ошибка: Невозможно обработать плейлист. Убедитесь, что запрос корректный и отправьте его повторно.'
				if er.code == 270:
					error_string = 'Правообладатель ограничил доступ к данной аудиозаписи. Загрузка прервана'
				sayOrReply(self.user_id, f'Ошибка: {error_string}', self.msg_id)
			logger.error(f'VK API: {er}')

		except Exception as er:
			if not self._playlist:
				error_string = 'Ошибка: Невозможно обработать плейлист. Убедитесь, что запрос корректный и отправьте его повторно.'
				sayOrReply(self.user_id, error_string, self.msg_id)
			logger.error(f'Исключение: {er}')

		finally:
			# Удаление сообщения с прогрессом
			if self.progress_msg_id:
				vk_bot.messages.delete(delete_for_all = 1, message_ids = self.progress_msg_id)

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
				if(userRequests[self.user_id] < 0):
					userRequests[self.user_id] += 1
					if (userRequests[self.user_id] == -1):
						userRequests[self.user_id] = 0
						vk_bot.messages.delete(delete_for_all = 1, message_ids = self.msg_start_id)
						audioTools.playlist_summarize(self.user_id)
				else:
					userRequests[self.user_id] -= 1
					vk_bot.messages.delete(delete_for_all = 1, message_ids = self.msg_start_id)

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
						userRequests[self.user_id],
						queueHandler.size_queue
					)
				)
				if not userRequests[self.user_id]: del userRequests[self.user_id]
				queueHandler.ack_request(self.user_id, threading.current_thread())
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
		self._stop = True


class QueueHandler():
	"""Класс управления очередью запросов."""

	def __init__(self):
		self._pool_req = []
		self._workers = {}

	@property
	def size_queue(self):
		return len(self._pool_req)

	@property
	def size_workers(self):
		size = 0
		for i in self._workers.values(): size += len(i)
		return size

	def clear_pool(self, user_id):
		"""Очистка очереди запросов пользователя."""
		try:
			if not userRequests.get(user_id):
				sayOrReply(user_id, 'Очередь запросов уже пуста!')
			else:
				for i in range(len(self._pool_req), 0, -1):
					if (self._pool_req[i-1][0][1] == user_id):
						del self._pool_req[i-1]
				if self._workers.get(user_id):
					for worker in self._workers.get(user_id):
						worker.stop()
					# Подведение отчёта о загрузке плейлиста (если он загружался)
					audioTools.playlist_summarize(user_id)
					del self._workers[user_id]
					del userRequests[user_id]
				sayOrReply(user_id, 'Очередь запросов очищена!')
		except Exception as er:
			logger.error(er)
			sayOrReply(user_id, 'Не удалось почистить очередь!')

	def add_new_request(self, task):
		"""Добавление нового запроса в общую очередь."""
		self._pool_req.append(task)
		#Проверка на превышение кол-ва максимально возможных воркеров
		if (self.size_workers < Settings.MAX_WORKERS): self._run_worker()

	def ack_request(self, user_id, worker):
		"""Подтверждение выполнения запроса."""
		try:
			self._workers.get(user_id).remove(worker)
			if not len(self._workers.get(user_id)): del self._workers[user_id]
			self._run_worker()

		except Exception as er:
			logger.error(er)
			if user_id in self._workers: del self._workers[user_id]
			for i in range(len(self._pool_req), 0, -1):
				if (self._pool_req[i-1][0][1] == user_id):
					del self._pool_req[i-1]

	def _run_worker(self):
		"""Запуск аудио воркера."""
		for i, task in enumerate(self._pool_req):
			user_id = task[0][1]

			# Если пользователь не имеет активных запросов
			if not self._workers.get(user_id):
				worker = AudioWorker(task)
				worker.name = f'{user_id}-worker <{len(self._workers.get(user_id, []))}>'
				worker.start()
				self._workers[user_id] = [worker]
				del self._pool_req[i]
				return
			# Если пользователь имеет активные запросы
			elif (len(self._workers.get(user_id)) < Settings.MAX_UNITS):
				worker = AudioWorker(task)
				worker.name = f'{user_id}-worker <{len(self._workers.get(user_id, []))}>'
				worker.start()
				self._workers[user_id].append(worker)
				del self._pool_req[i]
				return


class VkBotWorker():
	"""Класс прослушивания новых сообщений."""

	def __init__(self, program_version: str):
		self.program_version = program_version
		self.longpoll        = MyVkBotLongPoll(vk_bot_auth, str(os.environ['BOT_ID']).strip())
		# Обработка невыполненных запросов после обновления, краша бота
		unanswered_messages  = vk_bot.messages.getDialogs(unanswered=1)
		for user_message in unanswered_messages.get('items'):
			# Проверка на сообщение от пользователя, а не беседы
			msg_obj = user_message.get('message')
			if 'users_count' not in msg_obj:
				msg_obj['peer_id'] = msg_obj.pop('user_id')
				msg_obj['text']    = msg_obj.pop('body')
				self.message_handler(msg_obj)

	def message_handler(self, msg_obj):
		"""Обработка объекта сообщения."""
		user_id    = msg_obj.get('peer_id')
		message_id = msg_obj.get('id')

		options = list(filter(None, msg_obj.get('text').split('\n')))
		logger.debug(f'New message: ({len(options)}) {options}')

		# Специфичные команды
		if options:
			command = options[0].strip().lower()
			if(command == UserCommands.CLEAR.value):
				queueHandler.clear_pool(user_id)
				return
		# Инициализация ячейки конкретного пользователя
		if not userRequests.get(user_id):
			userRequests[user_id] = 0
		# Проверка на текущую загрузку плейлиста
		if userRequests.get(user_id) < 0:
			sayOrReply(user_id, 'Ошибка: Пожалуйста, дождитесь окончания загрузки плейлиста.')
			return
		# Проверка на максимальное число запросов за раз
		if userRequests.get(user_id) == Settings.MAX_REQUESTS_QUEUE:
			sayOrReply(user_id, 'Ошибка: Кол-во ваших запросов в общей очереди не может превышать {0}.'.format(Settings.MAX_REQUESTS_QUEUE))
			return
		# Проверка на превышения числа возможных аргументов запроса
		if len(options) > 5:
			sayOrReply(user_id, 'Ошибка: Слишком много аргументов.', message_id)
			return

		attachment_info = msg_obj.get('attachments')
		# logger.debug(attachment_info)
		# Обработка приложений к сообщению
		if attachment_info:
			try:
				logger.debug(f'Attachments info: ({len(attachment_info)}) {attachment_info[0].get("type")}')
				attachment_type = attachment_info[0].get('type')

				if attachment_type == 'video':
					video_info     = attachment_info[0].get('video')
					video_owner_id = video_info.get('owner_id')
					video_id       = video_info.get('id')

					video = f'{video_owner_id}_{video_id}'
					logger.debug(f'Attachment video: {video}')
					response = vk_agent.video.get(videos = video)

					video_url = response.get('items')[0].get('player')
					if len(options) > 4:
						options[0] = video_url
					else:
						options.insert(0, video_url)

				elif attachment_type == 'link':
					link_url = attachment_info[0].get('link').get('url')
					if options:
						if link_url != options[0]:
							logger.debug(f'Options[0] ({options[0]}) != attachment ({link_url})')
							options.insert(0, link_url)
					else:
						options.insert(0, link_url)

				else:
					# Вызов ошибки, если в сообщении нет текста и прикреплённые приложения не являются видео или ссылкой
					if not options:
						sayOrReply(user_id, 'Ошибка обработки запроса.', message_id)
						return

			except Exception as er:
				logger.warning(f'Attachment: {er}')
				if not options:
					sayOrReply(user_id, 'Ошибка: Невозможно обработать запрос. Возможно, вы прикрепили видео вместо ссылки на видео.', message_id)
					return
		# Вызов ошибки, если отсутствуют приложения и нет текста
		if not options:
			sayOrReply(user_id, 'Ошибка: Некорректный запрос.', message_id)
			return
		# Обработка запроса с плейлистом
		if (RequestIndex.INDEX_PLAYLIST.value in options[0]):
			if (userRequests.get(user_id)):
				sayOrReply(user_id, 'Ошибка: Для загрузки плейлиста очередь запросов должна быть пуста.')
				return

			if len(options) < 2:
				sayOrReply(user_id, 'Ошибка: Отсутствуют необходимые параметры для загрузки плейлиста.', message_id)
			elif len(options) > 2:
				sayOrReply(user_id, 'Ошибка: Неверные параметры для загрузки плейлиста.', message_id)
			else:
				# Создание задачи + вызов функции фрагментации плейлиста, чтобы свести запрос к обычной единице (одной ссылке)
				userRequests[user_id] = -1
				msg_start_id = sayOrReply(user_id, 'Запрос добавлен в очередь (плейлист)')
				task         = [[msg_start_id, user_id, message_id], options]
				threading.Thread(target = audioTools.playlist_processing(task)).start()
		else:
			# Создание задачи и её добавление в обработчик очереди
			userRequests[user_id] += 1
			msg_start_id = sayOrReply(user_id, 'Запрос добавлен в очередь ({0}/{1})'.format(userRequests.get(user_id), Settings.MAX_REQUESTS_QUEUE.value))
			task         = [[msg_start_id, user_id, message_id], options]
			queueHandler.add_new_request(task)

	def listen_longpoll(self):
		"""Прослушивание новый сообщений."""
		for event in self.longpoll.listen():
			if event.type != VkBotEventType.MESSAGE_NEW:
				continue
			msg_obj = event.obj.message
			# Проверка на сообщение от пользователя, а не беседы
			logger.debug(f'Получено новое сообщение: {msg_obj}')
			if msg_obj.get('from_id') == msg_obj.get('peer_id'):
				self.message_handler(msg_obj)


if __name__ == '__main__':
	"""Точка входа в программу."""
	# Доступные параметры запуска
	parser = ArgParser()
	parser.add_argument(
		"-v",
		"--version",
		default = "v1.0.0",
		help    = "Version of the bot")

	# Значение аргументов запуска по умолчанию
	program_version = "v1.0.0"

	# Обработка параметров запуска
	try:
		args = parser.parse_args()
	except Exception as er:
		parser.print_help()
	else:
		program_version = args.version.strip().lower()

	# Путь сохранения логов на удалённом сервере
	logger_path = f'../data/logs/{program_version}-{date.today()}.log'
	# Инициализация глобального logger
	loggerSetup.setup('logger', logger_path)
	# Подключение logger
	logger = logging.getLogger('logger')

	logger.info('Program started.')

	# Подгрузка .env файла на windows
	logger.info(f'Platform is {platform}')
	if platform == "win32":
		from dotenv import load_dotenv
		load_dotenv()

	# Инициализация класса для подключение к базе данных
	db = database.DataBase()

	logger.info(f'Filesystem encoding: {sys.getfilesystemencoding()}, Preferred encoding: {locale.getpreferredencoding()}')
	logger.info(f'Current version {program_version}, Bot Group ID: {str(os.environ["BOT_ID"]).strip()}')
	logger.info('Logging into VKontakte...')

	# Интерфейс для работы с аккаунтом агента (который необходим для загрузки аудио)
	vk_agent_auth   = vk_api.VkApi(token = str(os.environ["AGENT_TOKEN"]).strip())
	vk_agent_upload = vk_api.VkUpload(vk_agent_auth)
	vk_agent        = vk_agent_auth.get_api()

	# Интерфейс для работы с ботом
	vk_bot_auth = vk_api.VkApi(token = str(os.environ["BOT_TOKEN"]).strip())
	vk_bot      = vk_bot_auth.get_api()

	# Для отслеживания кол-ва запросов от одного пользователя по MAX_REQUESTS_QUEUE
	# (отрицательные значения — загрузка плейлиста, положительные — загрузка единичных песен)
	userRequests = dict()

	queueHandler = QueueHandler()
	audioTools   = AudioTools()
	vkBotWorker  = VkBotWorker(program_version)

	# Запуск listener
	logger.info('Begin listening.')

	while True:
		try:
			vkBotWorker.listen_longpoll()
		except vk_api.exceptions.ApiError as er:
			logger.error(f'VK API: {er}')

	logger.info('You will never see this.')

