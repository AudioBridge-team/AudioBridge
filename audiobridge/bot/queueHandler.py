#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import threading
from queue import Queue

from audiobridge.bot.audioWorker import AudioWorker
from audiobridge.common.config import Settings, ParametersType
from audiobridge.common import vars
from audiobridge.tools.sayOrReply import sayOrReply


logger        = logging.getLogger('logger')
settings_conf = Settings()
param_type    = ParametersType()

class QueueHandler():
	"""Класс управления очередью запросов пользователя.
	"""

	def __init__(self):
		"""Инициализация класса QueueHandler.
		"""
		self._pool_req = [] # Общая очередь запросов
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
				for i in range(self.size_queue-1, -1, -1):
					if (self._pool_req[i].get(param_type.USER_ID) == user_id):
						del self._pool_req[i]
				if self._workers.get(user_id):
					for worker in self._workers.get(user_id):
						worker.stop()
					# Подведение отчёта о загрузке плейлиста (если он загружался)
					vars.playlistHandler.summarize(user_id)
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
		logger.debug(f"{task}\nCurrent pool size = {self.size_queue}")
		self._run_worker()

	def ack_request(self, user_id: int, worker: threading.Thread):
		"""Подтверждение выполнения пользовательского запроса.

		Args:
			user_id (int): Идентификатор пользователя.
			worker (threading.Thread): Воркер.
		"""
		try:
			self._workers.get(user_id).remove(worker)
			if not len(self._workers.get(user_id)):
				del self._workers[user_id]
			self._run_worker()

		except Exception as er:
			logger.error(er)
			if user_id in self._workers:
				del self._workers[user_id]
			for i in range(self.size_queue-1, -1, -1):
				if self._pool_req[i].get(param_type.USER_ID) == user_id:
					del self._pool_req[i]

	def _run_worker(self):
		"""Запуск аудио воркера.
		"""
		# Проверка на превышение кол-ва максимально возможных воркеров и наличие запросов в очереди
		if (self.size_workers < settings_conf.MAX_WORKERS) and self.size_queue:
			for task in self._pool_req:
				user_id = task.get(param_type.USER_ID)
				# Если пользователь имеет активные запросы
				user_threads = len(self._workers.get(user_id, []))
				# Проверка на превышение кол-ва воркеров на одного юзера
				if user_threads < settings_conf.MAX_UNITS:
					worker = AudioWorker(task)
					worker.name = f'{user_id}-worker <{user_threads}>'
					worker.start()
					if not self._workers.get(user_id):
						self._workers[user_id] = []
					self._workers[user_id].append(worker)
					self._pool_req.remove(task)
					break
