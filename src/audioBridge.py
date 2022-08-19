#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, sys, time, locale, json, logging, threading, subprocess, argparse
from logging import StreamHandler, Formatter
from datetime import datetime

import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.utils import get_random_id

from config import Cfg
from commands import Commands
from CustomErrors import CustomError


class MyVkBotLongPoll(VkBotLongPoll):
	def listen(self):
		while True:
			try:
				for event in self.check():
					yield event
			except Exception as e:
				logger.error(e)


class AudioTools():

	def __init__(self):
		self.playlist_result = {}

	# работа со строкой времени
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

	# получить информацию о видео по ключу
	def getVideoInfo(self, key, url):
		return 'youtube-dl --max-downloads 1 --no-warnings --get-filename -o "%({0})s" {1}'.format(key, url)

	# получить информацию о плейлисте
	def getPlaylistInfo(self, filter, url):
		return 'youtube-dl --no-warnings --dump-json --newline {0} {1}'.format(filter, url)

	# обработка плейлиста
	def playlist_processing(self, task):
		logger.debug(f'Получил плейлист: {task}')
		param        = task[0]
		options      = task[1]
		msg_start_id = param[0]  #id сообщения с размером очереди (необходимо для удаления в конце обработки запроса)
		user_id      = param[1]  #id пользователя
		msg_id       = param[2]  #id сообщения пользователя (необходимо для ответа на него)

		urls = []  #url составляющих плейлист
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

			# получение urls и проверка общей продолжительности запроса
			while attempts != Cfg.MAX_ATTEMPTS.value:
				proc = subprocess.Popen(informationString, stdout = subprocess.PIPE, stderr = subprocess.PIPE, text = True, shell = True)
				line = str(proc.stdout.readline())
				while line:
					obj = json.loads(line.strip())
					totalTime += int(float(obj['duration']))
					if (totalTime > Cfg.MAX_VIDEO_DURATION.value):
						raise CustomError('Ошибка: Суммарная продолжительность будущих аудиозаписей не может превышать 3 часа!')
					urls.append([obj['webpage_url'], obj['title'].strip()])
					line = str(proc.stdout.readline())
				stdout, stderr = proc.communicate()

				#if (stderr and not urls):
				if (not stderr and urls):
					break

				logger.error(f'Getting playlist information ({attempts}): {stderr.strip()}')
				if ('HTTP Error 403' in stderr):
					attempts += 1
					time.sleep(Cfg.TIME_ATTEMPT.value)
					continue
				elif ('Sign in to confirm your age' in stderr):
					raise CustomError('Ошибка: Невозможно скачать плейлист из-за возрастных ограничений.')
				elif ('Video unavailable' in stderr):
					raise CustomError('Ошибка: Плейлист недоступен из-за авторских прав или по иным причинам.')
				else:
					raise CustomError('Ошибка: Неверные параметры скачивания и/или URL плейлиста.')

			if not totalTime:
				raise CustomError('Ошибка обработки плейлиста.')

			vk.messages.edit(peer_id = user_id, message = f'Запрос добавлен в очередь (плейлист: {len(urls)})', message_id = msg_start_id)

		except CustomError as er:
			vk.messages.send(peer_id = user_id, message = f'Произошла ошибка: {er}', reply_to = msg_id, random_id = get_random_id())

			# удаление сообщения с порядком очереди
			vk.messages.delete(delete_for_all = 1, message_ids = msg_start_id)
			del userRequests[user_id]
			logger.error(f'Произошла ошибка: {er}')

		except Exception as er:
			error_string = 'Ошибка: Невозможно обработать плейлист. Убедитесь, что запрос корректный и отправьте его повторно.'
			vk.messages.send(peer_id = user_id, message = error_string, reply_to = msg_id, random_id = get_random_id())

			# удаление сообщения с порядком очереди
			vk.messages.delete(delete_for_all = 1, message_ids = msg_start_id)
			del userRequests[user_id]
			logger.error(f'Поймал исключение: {er}')

		else:
			self.playlist_result[user_id] = {'msg_id' : msg_id}  # отчёт скачивания плейлиста
			for i, url in enumerate(urls):
				self.playlist_result[user_id][url[1]] = Cfg.PLAYLIST_UNSTATED.value
				userRequests[user_id] -= 1
				queueHandler.add_new_request([param, [url[0]], [i+1, len(urls)]])

	# подвести итог
	def playlist_summarize(self, user_id):
		try:
			if self.playlist_result.get(user_id):
				msg_summary = ''
				summary = {}
				msg_id = self.playlist_result[user_id]['msg_id']

				for title, status in self.playlist_result[user_id].items():
					if status == msg_id: continue
					if not summary.get(status):
						summary[status] = [title]
					else:
						summary[status].append(title)
				logger.debug(f'Сводка по плейлисту: {summary}')

				if summary.get(Cfg.PLAYLIST_SUCCESSFUL.value):
					msg_summary += 'Успешно:\n'
					for title in summary[Cfg.PLAYLIST_SUCCESSFUL.value]: msg_summary += ('• ' + title + '\n')
				if summary.get(Cfg.PLAYLIST_COPYRIGHT.value):
					msg_summary += '\nЗаблокировано из-за авторских прав:\n'
					for title in summary[Cfg.PLAYLIST_COPYRIGHT.value]: msg_summary += ('• ' + title + '\n')
				if summary.get(Cfg.PLAYLIST_UNSTATED.value):
					msg_summary += '\nНе загружено:\n'
					for title in summary[Cfg.PLAYLIST_UNSTATED.value]: msg_summary += ('• ' + title + '\n')
				del self.playlist_result[user_id]
				vk.messages.send(peer_id = user_id, message = msg_summary, reply_to = msg_id, random_id = get_random_id())

		except Exception as er:
			logger.error(er)
			vk.messages.send(peer_id = user_id, message = 'Ошибка: Не удалось загрузить отчёт.', random_id = get_random_id())


class AudioWorker(threading.Thread):

	def __init__(self, task: list):
		super(AudioWorker, self).__init__()
		self._stop = False
		self._task = task
		self._playlist = False

	def run(self):
		logger.info('AudioWorker: Запуск.')
		try:
			task = self._task

			if (len(task) == 3):
				self._playlist = True
				self.task_id = task[2][0]
				self.task_size = task[2][1]
			options = task[1]

			param = task[0]
			self.msg_start_id = param[0]    #id сообщения с размером очереди (необходимо для удаления в конце обработки запроса)
			self.user_id = param[1]         #id пользователя
			self.msg_id = param[2]          #id сообщения пользователя (необходимо для ответа на него)
			self.path = ''                  #путь сохранения файла
			self.progress_msg_id = 0        #id сообщения с прогрессом загрузки

			if options[0][0] == '-':
				logger.warning('Меня попытались крашнуть!')
				raise CustomError('Ошибка: Некорректный адрес Youtube-видео.')

			downloadString = 'youtube-dl --no-warnings --no-part --newline --id --extract-audio --audio-format mp3 --max-downloads 1 "{0}"'.format(options[0])
			cUpdateProcess = -1

			logger.debug(f'Получена задача: {task}')

			attempts = 0
			video_duration = -1
			while attempts != Cfg.MAX_ATTEMPTS.value:
				# проверка на соблюдение ограничения длительности видео (MAX_VIDEO_DURATION)
				proc = subprocess.Popen(audioTools.getVideoInfo('duration', options[0]), stdout = subprocess.PIPE, stderr = subprocess.PIPE, text = True, shell = True)
				stdout, stderr = proc.communicate()
				if (stderr):
					logger.error(f'Получение длительности видео ({attempts}): {stderr.strip()}')
					if ('HTTP Error 403' in stderr):
						attempts += 1
						time.sleep(Cfg.TIME_ATTEMPT.value)
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
			elif video_duration > Cfg.MAX_VIDEO_DURATION.value:
				raise CustomError('Ошибка: Длительность будущей аудиозаписи превышает 3 часа.')

			# обработка запроса с таймингами среза
			if len(options) > 3:
				startTime = audioTools.getSeconds(options[3])
				if startTime == -1:
					raise CustomError('Ошибка: Неверный формат времени среза.')
				audioDuration = video_duration - startTime
				if len(options) == 5:
					audioDuration = audioTools.getSeconds(options[4]) - startTime

			proc = subprocess.Popen(audioTools.getVideoInfo('id', options[0]), stdout = subprocess.PIPE, text = True, shell = True)
			self.path = proc.communicate()[0].strip()

			# загрузка файла
			attempts = 0
			while attempts != Cfg.MAX_ATTEMPTS.value:
				proc = subprocess.Popen(downloadString, stdout = subprocess.PIPE, stderr = subprocess.PIPE, text = True, shell = True)
				line = str(proc.stdout.readline())
				while line:
					if self._stop: return

					# поиск пути сохранения файла
					if 'Destination' in line and '.mp3' in line:
						self.path = line[line.find(':')+2:len(line)].strip()
						logger.debug(f'Путь: {self.path}')

					# обновление сообщения с процессом загрузки файла
					if ' of ' in line:
						if cUpdateProcess == -1:
							if self._playlist:
								self.progress_msg_id = vk.messages.send(peer_id = self.user_id, message = f'Загрузка началась [{self.task_id}/{self.task_size}]', random_id = get_random_id())
							else:
								self.progress_msg_id = vk.messages.send(peer_id = self.user_id, message = 'Загрузка началась', reply_to = self.msg_id, random_id = get_random_id())
						if cUpdateProcess == Cfg.MSG_PERIOD.value:
							progress = line[line.find(' '):line.find('КиБ/сек.') + 5].strip()
							if progress:
								vk.messages.edit(peer_id = self.user_id, message = progress, message_id = self.progress_msg_id)
							cUpdateProcess = 0
						if ' in ' in line:
							progress = line[line.find(' '):len(line)].strip()
							if progress:
								msg = progress
								if self._playlist: msg += f' [{self.task_id}/{self.task_size}]'
								vk.messages.edit(peer_id = self.user_id, message = msg, message_id = self.progress_msg_id)
						cUpdateProcess += 1
					line = str(proc.stdout.readline())
				stdout, stderr = proc.communicate()

				if (stderr):
					if ('HTTP Error 403' in stderr): #ERROR: unable to download video data: HTTP Error 403: Forbidden
						logger.warning(f'Поймал ошибку 403.')
						attempts += 1
						time.sleep(Cfg.TIME_ATTEMPT.value)
						continue
					else:
						logger.error(f'Скачивание видео ({attempts}): {stderr.strip()}')
						raise CustomError('Невозможно скачать видео!')
				else:
					break
			logger.debug(f'Скачивание видео, попытки: {attempts}')

			# проверка валидности пути сохранения файла
			if not self.path:
				logger.error(f'Путь: попытки: {attempts}')
				raise CustomError('Ошибка: Некорректный адрес Youtube-видео.')

			# проверка размера фалйа (необходимо из-за внутренних ограничений VK)
			if os.path.getsize(self.path) > Cfg.MAX_FILESIZE.value:
				raise CustomError('Размер аудиозаписи превышает 200 Мб!')
			else:
				os.rename(self.path, 'B' + self.path)
				self.path = 'B' + self.path

				if self._stop: return

				# создание аудиосегмента
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

				# поиск и коррекция данных аудиозаписи
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
				# загрузка аудиозаписи на сервера VK + её отправка получателю
				audio_obj = upload.audio(self.path, artist, self.title)
				audio_id = audio_obj.get('id')
				audio_owner_id = audio_obj.get('owner_id')
				attachment = f'audio{audio_owner_id}_{audio_id}'

				if self._playlist:
					vk.messages.send(peer_id = self.user_id, attachment = attachment, random_id = get_random_id())
					audioTools.playlist_result[self.user_id][self.title] = Cfg.PLAYLIST_SUCCESSFUL.value
				else:
					vk.messages.send(peer_id = self.user_id, attachment = attachment, reply_to = self.msg_id, random_id = get_random_id())

		except CustomError as er:
			if not self._playlist:
				vk.messages.send(peer_id = self.user_id, message = er, reply_to = self.msg_id, random_id = get_random_id())
			logger.error(f'Custom: {er}')

		except vk_api.exceptions.ApiError as er:
			if self._playlist:
				if er.code == 270 and self.title:
					audioTools.playlist_result[self.user_id][self.title] = Cfg.PLAYLIST_COPYRIGHT.value
			else:
				error_string = 'Ошибка: Невозможно обработать плейлист. Убедитесь, что запрос корректный и отправьте его повторно.'
				if er.code == 270:
					error_string = 'Правообладатель ограничил доступ к данной аудиозаписи. Загрузка прервана'
				vk.messages.send(peer_id = self.user_id, message = f'Ошибка: {error_string}', reply_to = self.msg_id, random_id = get_random_id())
			logger.error(f'Vk Api: {er}')

		except Exception as er:
			if not self._playlist:
				error_string = 'Ошибка: Невозможно обработать плейлист. Убедитесь, что запрос корректный и отправьте его повторно.'
				vk.messages.send(peer_id = self.user_id, message = error_string, reply_to = self.msg_id, random_id = get_random_id())
			logger.error(f'Exception: {er}')

		finally:
			# удаление сообщения с прогрессом
			if self.progress_msg_id:
				vk.messages.delete(delete_for_all = 1, message_ids = self.progress_msg_id)

			# удаление загруженного файла
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
				# удаление сообщения с порядком очереди
				if(userRequests[self.user_id] < 0):
					userRequests[self.user_id] += 1
					if (userRequests[self.user_id] == -1):
						userRequests[self.user_id] = 0
						vk.messages.delete(delete_for_all = 1, message_ids = self.msg_start_id)
						audioTools.playlist_summarize(self.user_id)
				else:
					userRequests[self.user_id] -= 1
					vk.messages.delete(delete_for_all = 1, message_ids = self.msg_start_id)

				logger.debug(('Завершено:\n'+
							'\tЗадача: {0}\n' +
							'\tПусть: {1}\n' +
							'\tОчередь текущего пользователя ({2}): {3}\n' +
							'\tОчередь текущего worker\'а: {4}').format(self._task, self.path, self.user_id, userRequests[self.user_id], queueHandler.size_queue))
				if not userRequests[self.user_id]: del userRequests[self.user_id]
				queueHandler.ack_request(self.user_id, threading.current_thread())
			else:
				logger.debug(('Завершено:\n'+
					'\tЗадача: {0}\n' +
					'\tПусть: {1}\n' +
					'\tОчередь текущего пользователя ({2}): null\n' +
					'\tОчередь текущего worker\'а: null').format(self._task, self.path, self.user_id))

	def stop(self):
		self._stop = True

class QueueHandler():
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

	# очистка очереди запросов пользователя
	def clear_pool(self, user_id):
		try:
			if not userRequests.get(user_id):
				vk.messages.send(peer_id = user_id, message = 'Очередь запросов уже пуста!', random_id = get_random_id())
			else:
				for i in range(len(self._pool_req), 0, -1):
					if (self._pool_req[i-1][0][1] == user_id):
						del self._pool_req[i-1]
				if self._workers.get(user_id):
					for worker in self._workers.get(user_id):
						worker.stop()

					audioTools.playlist_summarize(user_id)
					del self._workers[user_id]
					del userRequests[user_id]
				vk.messages.send(peer_id = user_id, message = 'Очередь запросов очищена!', random_id = get_random_id())
		except Exception as er:
			logger.error(er)
			vk.messages.send(peer_id = user_id, message = 'Не удалось почистить очередь!', random_id = get_random_id())

	# добавление нового запроса в общую очередь
	def add_new_request(self, task):
		self._pool_req.append(task)
		# проверка на превышение кол-ва максимально возможных воркеров
		if (self.size_workers < Cfg.MAX_WORKERS.value): self._run_worker()

	# подтверждение выполнения запроса
	def ack_request(self, user_id, worker):
		try:
			self._workers.get(user_id).remove(worker)
			if not len(self._workers.get(user_id)): del self._workers[user_id]
			#try:
			self._run_worker()
			#except Exception as er:
			#	logger.error(er)
		except Exception as er:
			logger.error(er)
			if user_id in self._workers: del self._workers[user_id]
			for i in range(len(self._pool_req), 0, -1):
				if (self._pool_req[i-1][0][1] == user_id):
					del self._pool_req[i-1]

	# запуск воркера
	def _run_worker(self):
		for i, task in enumerate(self._pool_req):
			user_id = task[0][1]

			# проверка на наличие и кол-во активных запросов пользователя
			if not self._workers.get(user_id):
				worker = AudioWorker(task)
				worker.name = f'{user_id}-worker <{len(self._workers.get(user_id, []))}>'
				worker.start()
				self._workers[user_id] = [worker]
				del self._pool_req[i]
				return

			elif (len(self._workers.get(user_id)) < Cfg.MAX_UNITS.value):
				worker = AudioWorker(task)
				worker.name = f'{user_id}-worker <{len(self._workers.get(user_id, []))}>'
				worker.start()
				self._workers[user_id].append(worker)
				del self._pool_req[i]
				return


class VkBotWorker():
	def __init__(self):
		self.longpoll = MyVkBotLongPoll(vk_session, str(os.environ['BOT_ID']))

	def sayOrReply(self, user_id, _message, _reply_to = None):
		if _reply_to:
			return vk.messages.send(peer_id = user_id, message = _message, reply_to = _reply_to, random_id = get_random_id())
		return vk.messages.send(peer_id = user_id, message = _message, random_id = get_random_id())

	def listen_longpoll(self, debug_mode = False):
		for event in self.longpoll.listen():
			if event.type != VkBotEventType.MESSAGE_NEW:
				continue

			msg = event.obj.message
			user_id = msg.get('peer_id')
			message_id = msg.get('id')
			if debug_mode:
				if not user_id in json.loads(os.environ['DEVELOPERS_ID']):
					#vk.messages.send(peer_id = user_id, message = 'Бот обновляется. Повторите свой запрос приблизительно через час.', reply_to = message_id, random_id = get_random_id())
					#self.sayOrReply(user_id, 'Бот обновляется. Повторите свой запрос приблизительно через час.', message_id)
					continue
			options = list(filter(None, event.obj.message.get('text').split('\n')))
			logger.debug(f'New message: ({len(options)}) {options}')

			if (options):
				command = options[0]
				if (command.strip().lower() == Commands.CLEAR.value):
					queueHandler.clear_pool(user_id)
					continue

			if not userRequests.get(user_id):
				userRequests[user_id] = 0

			if userRequests.get(user_id) < 0:
				#vk.messages.send(peer_id = user_id, message = 'Дождитесь окончания загрузки плейлиста!', random_id = get_random_id())
				self.sayOrReply(user_id, 'Ошибка: Пожалуйста, дождитесь окончания загрузки плейлиста.')
				continue

			if userRequests.get(user_id) == Cfg.MAX_REQUESTS_QUEUE.value:
				#vk.messages.send(peer_id = user_id, message = 'Ваше количество запросов в общей очереди не может превышать {0}!'.format(Cfg.MAX_REQUESTS_QUEUE.value), random_id = get_random_id())
				self.sayOrReply(user_id, 'Ошибка: Кол-во ваших запросов в общей очереди не может превышать {0}.'.format(Cfg.MAX_REQUESTS_QUEUE.value))
				continue

			if len(options) > 5:
				#vk.messages.send(peer_id = user_id, message = 'Слишком много аргументов!', reply_to = message_id, random_id = get_random_id())
				self.sayOrReply(user_id, 'Ошибка: Слишком много аргументов.', message_id)
				continue

			attachment_info = msg.get('attachments')
			#logger.debug(attachment_info)

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
						response = vk_user.video.get(videos = video)

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
						if not options:
							#vk.messages.send(peer_id = user_id, message = 'Ошибка обработки запроса!', reply_to = message_id, random_id = get_random_id())
							self.sayOrReply(user_id, 'Ошибка обработки запроса.', message_id)
							continue

				except Exception as er:
					logger.warning(f'Attachment: {er}')
					if not options:
						#vk.messages.send(peer_id = user_id, message = 'Невозможно обработать запрос (возможно, вы прикрепили видео вместо ссылки на видео)!', reply_to = message_id, random_id = get_random_id())
						self.sayOrReply(user_id, 'Ошибка: Невозможно обработать запрос. Возможно, вы прикрепили видео вместо ссылки на видео.', message_id)
						continue

			if not options:
				#vk.messages.send(peer_id = user_id, message = 'Некорректный запрос!', reply_to = message_id, random_id = get_random_id())
				self.sayOrReply(user_id, 'Ошибка: Некорректный запрос.', message_id)
				continue

			if (Cfg.INDEX_PLAYLIST.value in options[0]):
				if (userRequests.get(user_id)):
					#vk.messages.send(peer_id = user_id, message = 'Для загрузки плейлиста очередь запросов должна быть пуста!', random_id = get_random_id())
					self.sayOrReply(user_id, 'Ошибка: Для загрузки плейлиста очередь запросов должна быть пуста.')
					continue

				if len(options) < 2:
					#vk.messages.send(peer_id = user_id, message = 'Отсутствуют необходимые параметры для загрузки плейлиста!', reply_to = message_id, random_id = get_random_id())
					self.sayOrReply(user_id, 'Ошибка: Отсутствуют необходимые параметры для загрузки плейлиста.', message_id)
				elif len(options) > 2:
					#vk.messages.send(peer_id = user_id, message = 'Неверные параметры для загрузки плейлиста!', reply_to = message_id, random_id = get_random_id())
					self.sayOrReply(user_id, 'Ошибка: Неверные параметры для загрузки плейлиста.', message_id)
				else:
					userRequests[user_id] = -1
					#msg_start_id = vk.messages.send(peer_id = user_id, message = 'Запрос добавлен в очередь (плейлист)', random_id = get_random_id())
					msg_start_id = self.sayOrReply(user_id, 'Запрос добавлен в очередь (плейлист)')
					task = [[msg_start_id, user_id, message_id], options]
					threading.Thread(target = audioTools.playlist_processing(task)).start()
			else:
				userRequests[user_id] += 1
				#msg_start_id = vk.messages.send(peer_id = user_id, message = , random_id = get_random_id())
				msg_start_id = self.sayOrReply(user_id, 'Запрос добавлен в очередь ({0}/{1})'.format(userRequests.get(user_id), Cfg.MAX_REQUESTS_QUEUE.value))
				task = [[msg_start_id, user_id, message_id], options]
				queueHandler.add_new_request(task)


if __name__ == '__main__':
	parser = argparse.ArgumentParser()
	parser.add_argument("-v", "--version", help="Version of the bot")
	parser.add_argument("-d", "--debug", action='store_true', help="Debug mode")
	args = parser.parse_args()

	path_logs = "/AudioBridge-data/release/logs-release.log"
	if args.debug:
		path_logs = "/AudioBridge-data/debug/logs-debug.log"

	logger = logging.getLogger('logger')
	logging.basicConfig(filename=path_logs,
                    	filemode='a',
						#format = '[%(asctime)s, %(levelname)s] ~ %(threadName)s (%(funcName)s)\t~: %(message)s',
						format = '[%(asctime)s, %(levelname)s] ~ (%(funcName)s)\t~: %(message)s',
						datefmt = '%d-%m-%y %H:%M:%S',
						level=logging.DEBUG,
						stream=sys.stdout)

	logger.info('Program started.')
	logger.info(f'Debug mode is {args.debug}')
	logger.info(f'Filesystem encoding: {sys.getfilesystemencoding()}, Preferred encoding: {locale.getpreferredencoding()}')
	logger.info(f'Current version {args.version}, Bot Group ID: {os.environ["BOT_ID"]}, Developers ID: {os.environ["DEVELOPERS_ID"]}')
	logger.info('Logging into VKontakte...')

	vk_session_music = vk_api.VkApi(token = os.environ["AGENT_TOKEN"])
	upload           = vk_api.VkUpload(vk_session_music)
	vk_user          = vk_session_music.get_api()

	vk_session = vk_api.VkApi(token = os.environ["BOT_TOKEN"])
	vk         = vk_session.get_api()

	userRequests = {}  #для отслеживания кол-ва запросов от одного пользователя MAX_REQUESTS_QUEUE
	queueHandler, audioTools = None, None

	queueHandler = QueueHandler()
	audioTools   = AudioTools()
	vkBotWorker  = VkBotWorker()

	logger.info('Begin listening.')
	while True:
		try:
			vkBotWorker.listen_longpoll(debug_mode=args.debug)
		except vk_api.exceptions.ApiError as er:
			logger.error(f'VK API: {er}')
	logger.info('You will never see this.')


