#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import threading

from audiobridge.bot.audioWorker import AudioWorker
from audiobridge.utils.sayOrReply import sayOrReply
from audiobridge.utils.deleteMsg import deleteMsg
from audiobridge.utils.errorHandler import *

from audiobridge.config.bot import cfg as bot_cfg
from audiobridge.config.handler import vars, WorkerTask


logger = logging.getLogger('logger')

class QueueHandler():
    """Класс управления очередью запросов пользователя.
    """

    def __init__(self):
        """Инициализация класса QueueHandler.
        """
        self._pool_req = [] # Общая очередь запросов
        self._workers = {} 	# Список действующих воркеров.

    def size_queue(self) -> int:
        """Получение размера общей очереди запросов.

        Returns:
            int: Размер общей очереди запросов.
        """
        return len(self._pool_req)

    def size_workers(self) -> int:
        """Получение размера действующих воркеров.

        Returns:
            int: Размера действующих воркеров.
        """
        size = 0
        for i in self._workers.values(): size += len(i)
        return size

    def clear_pool(self, user_id: int, only_current = False):
        """Очистка очереди запросов пользователя.

        Args:
            user_id (int): Идентификатор пользователя.
        """
        try:
            # Вызов ошибки, если очередь уже пуста
            if not vars.userRequests.get(user_id):
                raise CustomError(ErrorType.queueProc.ALREADY_EMPTY)
            # Получение действующих воркеров
            user_workers = self._workers.get(user_id)
            # Если запрошен пропуск только текущей задачи
            if only_current:
                # Остановка последнего запущенного воркера и быстрое подтверждение его завершения
                track_name = "текущего трека"
                if user_workers:
                    current_task : AudioWorker = user_workers[-1]
                    if current_task.song_name:
                        track_name = f'трека "{current_task.song_name}"'
                    current_task.stop()
                    self.ack_request(user_id, current_task)
                sayOrReply(user_id, f'Загрузка {track_name} пропущена')
                return
            # Удаление из очереди всех запросов с id пользователя
            self._pool_req = list(filter(lambda obj: obj.user_id != user_id, self._pool_req))
            if user_workers:
                # Остановка всех запущенных воркеров (подтверждение здесь не нужно, т.к. объект пользователя удалён)
                worker : AudioWorker # type preannotation
                for worker in user_workers:
                    worker.stop()
                    deleteMsg(worker.msg_start)
                # Подведение отчёта о загрузке плейлиста (если загружался именно оны)
                vars.playlist.summarize(user_id)
                del self._workers[user_id]
            del vars.userRequests[user_id]
            sayOrReply(user_id, "Загрузка всех треков преврана")
        except CustomError as er:
            logger.debug(er)
            sayOrReply(user_id, er.description)
        except Exception as er:
            logger.error(er)
            sayOrReply(user_id, f"Ошибка: {ErrorType.queueProc.CANT_CLEAN.value}.")

    def add_new_request(self, task: WorkerTask):
        """Добавление нового пользовательского запроса в общую очередь.

        Args:
            task (WorkerTask): Пользовательского запрос, включающий в себя необходимую информацию для загрузки музыки.
        """
        self._pool_req.append(task)
        logger.debug(f"{task}\nCurrent pool size = {self.size_queue()}")
        self._run_worker()

    def ack_request(self, user_id: int, worker: threading.Thread):
        """Подтверждение выполнения пользовательского запроса.

        Args:
            user_id (int): Идентификатор пользователя.
            worker (threading.Thread): Воркер.
        """
        # Удаление сообщения с порядком очереди и уменьшение общего числа запросов пользователя
        if vars.userRequests[user_id] < 0:
            vars.userRequests[user_id] += 1
            if vars.userRequests[user_id] == -1:
                vars.userRequests[user_id] = 0
                deleteMsg(worker.msg_start)
                vars.playlist.summarize(user_id)
        elif vars.userRequests[user_id] > 0:
            vars.userRequests[user_id] -= 1
            deleteMsg(worker.msg_start)

        logger.debug(
            (
            'Завершено:\n'+
            '\tОчередь текущего пользователя ({}): {}\n' +
            '\tОчередь текущего worker\'а: {}'
            )
            .format(
                user_id,
                vars.userRequests[user_id],
                self.size_queue()
            )
        )
        # Очистка памяти
        if not vars.userRequests[user_id]:
            del vars.userRequests[user_id]
        user_workers : list = self._workers.get(user_id)
        if user_workers:
            user_workers.remove(worker)
            if not user_workers: del self._workers[user_id]
        # Обработка следующей задачи из очереди
        self._run_worker()

    def _run_worker(self):
        """Запуск аудио воркера.
        """
        logger.debug(f"Current workers size: {self.size_workers()}/{bot_cfg.settings.max_workers}")
        # Проверка на превышение кол-ва максимально возможных воркеров и наличие запросов в очереди
        if (self.size_workers() >= bot_cfg.settings.max_workers) or (not self.size_queue()): return
        task : WorkerTask
        for task in self._pool_req:
            user_id = task.user_id
            # Если пользователь имеет активные запросы
            user_threads = len(self._workers.get(user_id, []))
            # Проверка на превышение кол-ва воркеров на одного юзера
            if user_threads >= bot_cfg.settings.max_units: continue
            worker = AudioWorker(task)
            worker.name = f'{user_id}-worker <{user_threads}>'
            worker.start()
            if not self._workers.get(user_id):
                self._workers[user_id] = []
            self._workers[user_id].append(worker)
            # Удаление задачи из очереди
            self._pool_req.remove(task)
            break
