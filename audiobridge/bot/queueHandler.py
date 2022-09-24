#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import threading

from audiobridge.bot.audioWorker import AudioWorker
from audiobridge.common.config import Settings
from audiobridge.common import vars
from audiobridge.tools.sayOrReply import sayOrReply


logger = logging.getLogger('logger')

class QueueHandler():
	"""Класс управления очередью запросов пользователя.
	"""

	def __init__(self):
		"""Инициализация класса QueueHandler.
		"""
		self._pool_req = [] # Размер общей очереди запросов
		self._workers = {} 	# Список действующих воркеров.

	@property
	def size_queue(self) -> int:
		"""Параметр размера общей очереди запросов.

		Returns:
			int: Размер общей очереди запросов.
		"""
		return len(self._pool_req)

	@property
	def size_workers(self) -> int:
		"""Параметр размера действующих воркеров.

		Returns:
			int: Размера действующих воркеров.
		"""
		size = 0
		for i in self._workers.values(): size += len(i)
		return size

	def clear_pool(self, user_id: int):
		"""Очистка очереди запросов пользователя.

		Args:
			user_id (int): Идентификатор пользователя.
		"""
		try:
			if not vars.userRequests.get(user_id):
				sayOrReply(user_id, 'Очередь запросов уже пуста!')
			else:
				for i in range(len(self._pool_req), 0, -1):
					if (self._pool_req[i-1][0][1] == user_id):
						del self._pool_req[i-1]
				if self._workers.get(user_id):
					for worker in self._workers.get(user_id):
						worker.stop()
					# Подведение отчёта о загрузке плейлиста (если он загружался)
					vars.audioTools.playlist_summarize(user_id)
					del self._workers[user_id]
					del vars.userRequests[user_id]
				sayOrReply(user_id, 'Очередь запросов очищена!')
		except Exception as er:
			logger.error(er)
			sayOrReply(user_id, 'Не удалось почистить очередь!')

	def add_new_request(self, task: dict):
		"""Добавление нового пользовательского запроса в общую очередь.

		Args:
			task (dict): Пользовательского запрос, включающий в себя необходимую информацию для загрузки музыки.
		"""
		self._pool_req.append(task)
		# Проверка на превышение кол-ва максимально возможных воркеров
		if (self.size_workers < Settings.MAX_WORKERS): self._run_worker()

	def ack_request(self, user_id: int, worker: threading.Thread):
		"""Подтверждение выполнения пользовательского запроса.

		Args:
			user_id (int): Идентификатор пользователя.
			worker (threading.Thread): Воркер.
		"""
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
		"""Запуск аудио воркера.
		"""
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
