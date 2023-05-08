#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import yt_dlp

from audiobridge.utils.errorHandler import *
from audiobridge.utils.sayOrReply import sayOrReply
from audiobridge.utils.deleteMsg import deleteMsg
from audiobridge.utils.yt_dlpShell import Yt_dlpShell

from audiobridge.config.bot import cfg as bot_cfg
from audiobridge.config.handler import vars, WorkerTask


logger    = logging.getLogger('logger')
MSG_REPLY = 'msg_reply'
# Опции для модуля yt_dlp
ydl_opts = {
    'logger': Yt_dlpShell(),
    "extract_flat": True,
    'nocheckcertificate': True,
    'retries': bot_cfg.settings.max_attempts
}

class PlaylistHandler():
    """Класс вспомогательных инструментов для обработки запроса.

    Raises:
        CustomError: Вызов ошибки с настраиваемым содержанием.
    """
    def __init__(self):
        """Инициализация класса PlaylistHandler.
        """
        self.playlist_result = {}

    def extract_elements(self, task: WorkerTask):
        """Обработка плейлиста: извлечение его составляющих.

        Args:
            task (dict): Пользовательский запрос.

        Raises:
            CustomError:  Вызов ошибки с настраиваемым содержанием.
        """
        logger.debug(f'Получил плейлист: {task}')

        user_id = task.user_id
        msg_reply = task.msg_reply
        msg_start = task.msg_start

        urls = [] # url составляющих плейлист
        try:
            totalTime = 0
            # Проверка на наличие строки в запросе с номерами необходимых элементов плейлиста
            ydl_opts['playlist_items'] = task.pl_param
            # Извлечение полной информации о всех доступных и недоступных видео из плейлиста
            pl_info = yt_dlp.YoutubeDL(ydl_opts).extract_info(task.url, download=False)
            for entry in pl_info['entries']:
                if not entry: continue
                url   = entry.get("url", None)
                title = entry.get("title", None)
                if not (url and title): continue
                urls.append([url, title])

                duration = entry.get("duration", None)
                totalTime += int(float(duration))
                if totalTime > bot_cfg.settings.max_video_duration:
                    raise CustomError(ErrorType.plProc.EXCEED_DURATION)

            if not urls:
                raise CustomError(ErrorType.plProc.NO_AVAILABLE_PARTS)
            vars.api.bot.messages.edit(peer_id = user_id, message = f'Запрос добавлен в очередь (плейлист: {len(urls)})', message_id = msg_start)

        except CustomError as er:
            sayOrReply(user_id, er.description, msg_reply)
            # Запись ошибки в таблицу `vk_messages`
            vars.db.set_error_code(msg_reply, er.code)

            # Удаление сообщения с порядком очереди
            deleteMsg(msg_start)
            # Очистка памяти
            del vars.userRequests[user_id]
            logger.error(f'Custom: {er}')

        except Exception as er:
            error_string = "Ошибка: Невозможно обработать плейлист. Убедитесь, что запрос корректный и отправьте его повторно."
            sayOrReply(user_id, error_string, msg_reply)
            # Запись ошибки в таблицу `vk_messages`
            vars.db.set_error_code(msg_reply, er)

            # Удаление сообщения с порядком очереди
            deleteMsg(msg_start)
            # Очистка памяти
            del vars.userRequests[user_id]
            logger.error(f'Поймал исключение: {er}')

        else:
            # Отчёт скачивания плейлиста
            self.playlist_result[user_id] = {MSG_REPLY : msg_reply}
            task.pl_size = len(urls)
            for i, url in enumerate(urls):
                self.playlist_result[user_id][i+1] = [bot_cfg.playlistStates.PLAYLIST_UNSTATED, url[1]]
                vars.userRequests[user_id] -= 1

                sub_task = task
                sub_task.url = url[0]
                sub_task.pl_element = i+1

                # Добавление в очередь разбитого на подзадачи запроса
                vars.queue.add_new_request(sub_task)

    def summarize(self, user_id: int):
        """Подведение отчёта об обработки плейлиста.

        Args:
            user_id (_type_): Идентификатор пользователя.
        """
        try:
            if not self.playlist_result.get(user_id): return
            msg_summary = ""
            summary     = {}
            msg_reply      = self.playlist_result[user_id][MSG_REPLY]

            for task_id, info in self.playlist_result[user_id].items():
                if task_id == MSG_REPLY:
                    continue
                if not summary.get(info[0]):
                    summary[info[0]] = [info[1]]
                else:
                    summary[info[0]].append(info[1])
            logger.debug(f'Сводка по плейлисту: {summary}')

            if summary.get(bot_cfg.playlistStates.PLAYLIST_SUCCESSFUL):
                msg_summary += 'Успешно:\n'
                for title in summary[bot_cfg.playlistStates.PLAYLIST_SUCCESSFUL]: msg_summary += ('• ' + title + '\n')
            if summary.get(bot_cfg.playlistStates.PLAYLIST_COPYRIGHT):
                msg_summary += '\nЗаблокировано из-за авторских прав:\n'
                for title in summary[bot_cfg.playlistStates.PLAYLIST_COPYRIGHT]: msg_summary += ('• ' + title + '\n')
            if summary.get(bot_cfg.playlistStates.PLAYLIST_UNSTATED):
                msg_summary += '\nНе загружено:\n'
                for title in summary[bot_cfg.playlistStates.PLAYLIST_UNSTATED]: msg_summary += ('• ' + title + '\n')
            del self.playlist_result[user_id]
            sayOrReply(user_id, msg_summary, msg_reply)

        except Exception as er:
            logger.error(er)
            sayOrReply(user_id, "Ошибка: Не удалось загрузить отчёт.")
