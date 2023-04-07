#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import threading
import vk_api
from vk_api.bot_longpoll import VkBotEventType

from audiobridge.tools.myVkBotLongPoll import MyVkBotLongPoll
from audiobridge.commands.user import UserCommands
from audiobridge.tools.sayOrReply import sayOrReply

from audiobridge.config.bot import cfg as bot_cfg
from audiobridge.config.handler import vars, WorkerTask


logger = logging.getLogger('logger')

class VkBotWorker():
    """Обработка пользовательских запросов.
    """

    def __init__(self, vk_bot_auth: vk_api.VkApi):
        """Инициализация класса VkBotWorker.

        Args:
            vk_bot_auth (vk_api.VkApi) Апи бота в группе Вк.
        """
        self.longpoll = MyVkBotLongPoll(vk_bot_auth, bot_cfg.auth.id)

    def command_handler(self, msg_options: list, user_id: int) -> bool:
        """Обработка пользовательских команд.

        Args:
            msg_options (list): Сообщение пользователя в виде списка аргументов.
            user_id (int): Идентификатор пользователя.

        Returns:
            bool: Успешность обработки команды.
        """
        command = msg_options[0].lower()
        if command == UserCommands.CLEAR.value:
            vars.queue.clear_pool(user_id)
            return True
        return False

    def vk_video_handler(self, video_url: str) -> str:
        """Получения прямой ссылки из внутренней ссылки Вк для скачивания прикреплённого видео.

        Args:
            video_url (str): Внутренняя ссылка прикреплённого Вк видео.

        Returns:
            str: Прямая ссылка на скачивание прикреплённого видео.
        """
        video_url = video_url[video_url.find(bot_cfg.reqIndex.INDEX_VK_VIDEO) + len(bot_cfg.reqIndex.INDEX_VK_VIDEO):]
        logger.debug(f'Vk video info: {video_url}')
        response = vars.api.agent.video.get(videos = video_url)
        items = response.get('items')
        if not items:
            return ''
        return items[0].get('player')

    def message_handler(self, msg_obj: dict):
        """Обработка пользовательских сообщений

        Args:
            msg_obj (dict): Объект сообщения.
        """
        user_id    = msg_obj.get('peer_id')
        msg_id   = msg_obj.get('id')
        msg_body = str(msg_obj.get('text'))

        # Обработка ответов пользователей на сообщения модераторов
        if msg_obj.get('reply_message'):
            logger.debug(f"Ответ на сообщение модератора/бота: {msg_body}")
            return

        options = list(map(str.strip, filter(None, msg_body.split('\n'))))
        logger.debug(f'New message: ({len(options)}) {options}')
        # Обработка команд
        if msg_body.startswith('/'):
            if self.command_handler(options, user_id):
                logger.debug("Command was processed")
            else:
                logger.debug("Command doesn't exist")
                sayOrReply(user_id, "Ошибка: Данной команды не существует.\nВведите /help для просмотра доступных команд.")
            return

        # Инициализация ячейки конкретного пользователя
        if not vars.userRequests.get(user_id):
            vars.userRequests[user_id] = 0
        # Проверка на текущую загрузку плейлиста
        if vars.userRequests.get(user_id) < 0:
            sayOrReply(user_id, "Ошибка: Пожалуйста, дождитесь окончания загрузки плейлиста.")
            return
        # Проверка на максимальное число запросов за раз
        if vars.userRequests.get(user_id) == bot_cfg.settings.max_requests_queue:
            sayOrReply(user_id, "Ошибка: Кол-во ваших запросов в общей очереди не может превышать {0}.".format(bot_cfg.settings.max_requests_queue))
            return
        # Проверка на превышения числа возможных аргументов запроса
        if len(options) > 4:
            sayOrReply(user_id, "Ошибка: Неверный формат запроса. Узнать правильный вы сможете в инструкции (закреплённый пост в группе)", msg_id)
            return
        # Проверка возможных приложений, если отсутствует какой-либо текст в сообщении
        if not options:
            attachment_info = msg_obj.get('attachments')
            # logger.debug(attachment_info)
            # Обработка приложений к сообщению
            if attachment_info:
                try:
                    logger.debug(f'Attachments info: ({len(attachment_info)}) {attachment_info[0].get("type")}')

                    attachment_type = attachment_info[0].get("type")
                    if attachment_type == 'video':
                        video_info     = attachment_info[0].get('video')
                        video_owner_id = video_info.get('owner_id')
                        video_id       = video_info.get('id')
                        video_platform = video_info.get("platform", "undefined")

                        video = f'{video_owner_id}_{video_id}'
                        logger.debug(f'Attachment video: {video} (platform: {video_platform})')
                        options = [ f'https://{bot_cfg.reqIndex.INDEX_VK_VIDEO}{video}' ] if video_platform != bot_cfg.reqIndex.INDEX_PLATFORM_YOUTUBE else [ video_platform ]

                    elif attachment_type == 'link':
                        options = [ attachment_info[0].get('link').get('url') ]

                except Exception as er:
                    logger.warning(f'Attachment: {er}')
                    sayOrReply(user_id, "Ошибка: Невозможно обработать прикреплённое видео. Пришлите ссылку.", msg_id)
                    return

        # Вызов ошибки при наличии прикреплённого YouTube видео
        if bot_cfg.reqIndex.INDEX_PLATFORM_YOUTUBE in options:
            sayOrReply(user_id, "Ошибка: Невозможно обработать прикреплённое YouTube видео. Отправьте ссылку в текстовом виде.", msg_id)
            return
        # Безопасный метод проверки, наподобие list.get()
        if not next(iter(options), '').startswith(bot_cfg.reqIndex.INDEX_URL):
            sayOrReply(user_id, "Не обнаружена ссылка для скачивания.", msg_id)
            return
        # Обработка запроса с плейлистом
        if bot_cfg.reqIndex.INDEX_PLAYLIST in options[0]:
            # Проверка на отсутствие других задач от данного пользователя
            if (vars.userRequests.get(user_id)):
                sayOrReply(user_id, 'Ошибка: Для загрузки плейлиста очередь запросов должна быть пустой.')
                return
            # Проверка на корректность запроса
            if len(options) > 2:
                sayOrReply(user_id, "Ошибка: Слишком много параметров для загрузки плейлиста.", msg_id)
                return
            # Создание задачи + вызов функции фрагментации плейлиста, чтобы свести запрос к обычной единице (одной ссылке)
            vars.userRequests[user_id] = -1
            msg_start_id = sayOrReply(user_id, "Запрос добавлен в очередь (плейлист)")
            task = WorkerTask(msg_start_id, user_id, msg_id, options[0])
            task.pl_type = True
            if len(options) == 2: task.pl_param = options[1].replace(' ', "")
            threading.Thread(target = vars.playlist.extract_elements(task)).start()
            return
        # Обработка обычного запроса
        # Обработка YouTube Shorts
        if bot_cfg.reqIndex.INDEX_YOUTUBE_SHORTS in options[0]:
            logger.debug("Обнаружен YouTube Shorts. Замена ссылки...")
            options[0] = options[0].replace(bot_cfg.reqIndex.INDEX_YOUTUBE_SHORTS, "/watch?v=")
        # Обработка Vk Video
        elif bot_cfg.reqIndex.INDEX_VK_VIDEO in options[0]:
            logger.debug("Обнаружено Vk video. Получение прямой ссылки...")
            video_url = self.vk_video_handler(options[0])
            if not video_url:
                sayOrReply(user_id, "Ошибка: Невозможно обработать прикреплённое видео, т.к. оно скрыто настройками приватности автора", msg_id)
                return
            options[0] = video_url
        # Создание задачи и её добавление в обработчик очереди
        vars.userRequests[user_id] += 1
        msg_start_id = sayOrReply(user_id, "Запрос добавлен в очередь ({0}/{1})".format(vars.userRequests.get(user_id), bot_cfg.settings.max_requests_queue))
        task = WorkerTask(msg_start_id, user_id, msg_id, *options)
        vars.queue.add_new_request(task)

    def listen_longpoll(self):
        """Прослушивание новых сообщений от пользователей.
        """
        logger.debug("Started.")
        self.unanswered_message_handler()
        for event in self.longpoll.listen():
            logger.info(event.type)
            # Проверка на НОВОЕ сообщение от пользователя, а НЕ от беседы
            if event.type != VkBotEventType.MESSAGE_NEW or not event.from_user:
                continue
            msg_obj = event.obj.message
            # logger.debug(f'Получено новое сообщение: {msg_obj}')
            self.message_handler(msg_obj)

    def unanswered_message_handler(self):
        """Обработка невыполненных запросов после обновления, краша бота.
        """
        unanswered_messages = vars.api.bot.messages.getDialogs(unanswered=1)
        logger.debug(f"Number of unanswered massages: {len(unanswered_messages.get('items'))}")
        for user_message in unanswered_messages.get('items'):
            # Проверка на сообщение от пользователя, а не беседы
            msg_obj = user_message.get('message')
            if 'users_count' not in msg_obj:
                msg_obj['peer_id'] = msg_obj.pop('user_id')
                msg_obj['text']    = msg_obj.pop('body')
                self.message_handler(msg_obj)
