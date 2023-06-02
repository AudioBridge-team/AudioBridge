#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import json
import threading
import vk_api
from vk_api.bot_longpoll import VkBotEventType

from audiobridge.utils.errorHandler import *
from audiobridge.utils.myVkBotLongPoll import MyVkBotLongPoll
from audiobridge.commands import commands
from audiobridge.utils.sayOrReply import sayOrReply

from audiobridge.config.bot import cfg as bot_cfg
from audiobridge.config.handler import vars, WorkerTask

from audiobridge.keyboards.keyboard import keys
from audiobridge.keyboards import keyboards

from audiobridge.db.dbEnums import MessageType, UserData, UserRoles

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

    def command_handler(self, msg_options: list, user_id: int, is_keyboard: bool, user_obj: dict) -> bool:
        """Обработка пользовательских команд.

        Args:
            msg_options (list): Сообщение пользователя в виде списка аргументов.
            user_id (int)     : Идентификатор пользователя.
            is_keyboard (bool): Была ли команда вызвана с клавиатуры.

        Returns:
            bool: Успешность обработки команды.
        """
        # Получение карточки пользователя из таблицы `users`
        user_role = user_obj.get(UserData.ROLE, UserRoles.USER)
        msg_cmd = msg_options[0].lower()[1:]
        # Опции без самой команды
        msg_options = msg_options[1:]
        if is_keyboard:
            for kb in keyboards:
                if kb.command != msg_cmd: continue
                sayOrReply(user_id, "Выберите действие:", _keyboard = kb.keyboard(msg_options, user_id, bool(user_obj.get(UserData.TOKEN))))
                return True

        for cmd in commands:
            if cmd.name != msg_cmd or cmd.userRole > user_role: continue
            if msg_cmd == "help": msg_options = user_role
            cmd.run(user_id, msg_options)
            return True
        return False

    def vk_audio_rename(self, user_id: int, msg_obj: dict, new_values: list, user_token: str) -> bool:
        """Переименовка песни в вк.

        Args:
            msg_obj (dict)          : Объект сообщения.
            new_values (msg_options): Текст сообщения, разбитый по строчкам

        Returns:
            bool: Успешность переименовки.
        """
        # Была ли песня отправлена ботом
        if -msg_obj.get('from_id') != bot_cfg.auth.id: return False
        attachments = msg_obj.get('attachments')
        # Прикреплено ли к сообщению приложение
        if not attachments: return False
        # Явлляется ли приложение песней
        if attachments[0].get('type') != "audio": return False
        audio_obj    = attachments[0].get('audio')
        audio_id     = audio_obj.get('id')
        audio_owner  = audio_obj.get('owner_id')
        audio_title  = audio_obj.get('title')
        audio_author = audio_obj.get('artist')
        logger.debug(f"Получен запрос на переименовывание песни:\naudio_id: {audio_id}\naudio_owner: {audio_owner}\nold_title: {audio_title}\nold_artist: {audio_author}")
        if len(new_values) == 1:
            audio_title = new_values[0]
        elif len(new_values) == 2:
            audio_title  = new_values[0]
            audio_author = new_values[1]
        else: raise CustomError(ErrorType.userReq.BAD_RENAME_FORMAT)
        if len(audio_title) > 50: audio_title = audio_title[0:51]
        if len(audio_author) > 50: audio_author = audio_author[0:51]
        try:
            api_agent = vars.api.agent
            vk_user_auth = self._get_user_auth(user_token)
            if vk_user_auth and audio_owner == user_id:
                api_agent = vk_user_auth.get_api()
            api_agent.audio.edit(audio_id=audio_id, owner_id=audio_owner, title=audio_title, artist=audio_author)
        except vk_api.exceptions.ApiError as er:
            logger.error(f"Vk error ({er.code}): {er}")
            if er.code == 15: raise CustomError(ErrorType.userReq.DENIED_RENAMING)
            raise CustomError(ErrorType.userReq.CANT_RENAME_AUDIO)

        except Exception as er:
            logger.error(f"Unexpected error: {er}")
            raise CustomError(ErrorType.userReq.CANT_RENAME_AUDIO)
        return True

    def _get_user_auth(self, user_token: str) -> vk_api.VkApi:
        """Получение api пользователя.

        Args:
            user_id (int): Id пользователя.

        Returns:
            vk_api.VkApi: Api пользователя.
        """
        vk_user_auth : vk_api.VkApi = None
        try:
            if user_token: vk_user_auth = vk_api.VkApi(token = user_token)
            else: logger.debug("User token is NULL")
        except Exception as er:
            logger.warning(f"Can't auth into user account: {er}")
        return vk_user_auth

    def attachment_handler(self, attachment_info: list, vk_user_auth: vk_api.VkApi) -> list:
        """Обработка приложения.

        Args:
            attachment_info (list): Объект приложения.
            vk_user_auth (str): Api пользователя для обработки прикрепленных видео.

        Returns:
            list: Массив с параматрами для загрузки.
        """
        res = ''
        if not attachment_info: raise CustomError(ErrorType.userReq.NO_URL)
        try:
            attachment_type = attachment_info[0].get('type')
            logger.debug(f"Attachments info: ({len(attachment_info)}) {attachment_type}")

            if attachment_type == 'video':
                video_info     = attachment_info[0].get('video')
                video_owner_id = video_info.get('owner_id')
                video_id       = video_info.get('id')
                video_platform = video_info.get('platform', 'undefined')
                access_key     = video_info.get('access_key')

                video = f'{video_owner_id}_{video_id}'
                if access_key: video += '_' + access_key
                logger.debug(f'Attachment video: {video} (platform: {video_platform})\nПолучение прямой ссылки...')

                api_agent = vars.api.agent
                if vk_user_auth: api_agent = vk_user_auth.get_api()

                items = api_agent.video.get(videos = video).get('items')
                if not items: raise CustomError(ErrorType.userReq.PRIVATE_ATTACH)
                res = items[0].get('player')

            elif attachment_type == 'link':
                res = attachment_info[0].get('link').get('url')

        except CustomError as er:
            raise er

        except Exception as er:
            logger.warning(f'Attachment: {er}')
            raise CustomError(ErrorType.userReq.CANT_HANDLE_ATTACH)

        if not res.startswith("http"):
            raise CustomError(ErrorType.userReq.NO_URL)
        return res


    def message_handler(self, msg_obj: dict):
        """Обработка пользовательских сообщений

        Args:
            msg_obj (dict): Объект сообщения.
        """
        msg_type          : int          = MessageType.UNDEFINED
        error_description : str          = None
        vk_user_auth      : vk_api.VkApi = None

        user_id  = msg_obj.get('peer_id')
        msg_id   = msg_obj.get('id')
        msg_body = str(msg_obj.get('text', ''))
        msg_kb  = msg_obj.get('payload')

        task : WorkerTask = None
        try:
            options = []
            # Адаптация команды под общий вид запроса
            if msg_kb:
                cmd_obj = dict(json.loads(msg_kb))
                options.append("/" + cmd_obj.get(keys.CMD))
                options += cmd_obj.get(keys.ARGS, [])
                msg_body = options[0]
            else:
                options = list(map(str.strip, filter(None, msg_body.split('\n'))))

            logger.debug(f'New message: ({len(options)}) {options}')
            user_obj = vars.db.select_user_data(user_id)
            # Обработка ответов пользователей на сообщения модераторов
            reply_message = msg_obj.get('reply_message')
            if reply_message:
                msg_type = MessageType.PLAIN
                logger.debug(f"Ответ на сообщение модератора/бота: {msg_body}")
                if self.vk_audio_rename(user_id, reply_message, options, user_obj.get(UserData.TOKEN)):
                    msg_type = MessageType.AUDIO_RENAME
                    sayOrReply(user_id, "Аудиозапись успешно переименована")
                return

            # Обработка команд
            if msg_body.startswith('/'):
                msg_type = MessageType.COMMAND
                args = options
                if not msg_kb: args = msg_body.lower().split()
                if not self.command_handler(args, user_id, bool(msg_kb), user_obj):
                    raise CustomError(ErrorType.cmdProc.BAD_COMMAND)
                logger.debug("Command has been successfully handled")
                return

            # Инициализация ячейки конкретного пользователя
            if user_id not in vars.userRequests: vars.userRequests[user_id] = 0
            # Проверка на текущую загрузку плейлиста
            if vars.userRequests[user_id] < 0:
                raise CustomError(ErrorType.userReq.WAIT_FOR_PLAYLIST)
            # Проверка на максимальное число запросов за раз
            if vars.userRequests[user_id] >= bot_cfg.settings.max_requests_queue:
                raise CustomError(ErrorType.userReq.EXCEED_REQUEST_LIMIT)
            # Проверка на превышения числа возможных аргументов запроса
            if len(options) > 4:
                raise CustomError(ErrorType.userReq.BAD_REQUEST_FORMAT)

            vk_user_auth = self._get_user_auth(user_obj.get(UserData.TOKEN))
            # Проверка возможных приложений, если отсутствует какой-либо текст в сообщении
            if not options:
                options.append(self.attachment_handler(msg_obj.get('attachments'), vk_user_auth))
                msg_body = options[0]

            if not options[0].startswith("http"):
                options.insert(0, self.attachment_handler(msg_obj.get('attachments'), vk_user_auth))
                msg_body = options[0] + '\n' + msg_body
            # Проверка на динамическую ссылку
            if any(index.value in options[0] for index in bot_cfg.dynLinksIndex):
                raise CustomError(ErrorType.userReq.DYNAMIC_LINK)

            # Обработка запроса с плейлистом
            if "/playlist" in options[0]:
                # Проверка на отсутствие других задач от данного пользователя
                if vars.userRequests[user_id]:
                    raise CustomError(ErrorType.userReq.BUSY_PLAYLIST_QUEUE)
                # Проверка на корректность запроса
                if len(options) > 2:
                    raise CustomError(ErrorType.userReq.BAD_PLAYLIST_REQUEST)
                # Создание задачи + вызов функции фрагментации плейлиста, чтобы свести запрос к обычной единице (одной ссылке)
                vars.userRequests[user_id] = -1
                msg_start_id = sayOrReply(user_id, "Запрос добавлен в очередь (плейлист)")
                task = WorkerTask(msg_start_id, user_id, msg_id, options[0])
                task.pl_type = True
                if len(options) == 2: task.pl_param = options[1].replace(' ', "")
                msg_type = MessageType.PLAYLIST
                return
            # Обработка обычного запроса

            # Создание задачи и её добавление в обработчик очереди
            vars.userRequests[user_id] += 1
            msg_start_id = sayOrReply(user_id, "Запрос добавлен в очередь ({0}/{1})".format(vars.userRequests[user_id], bot_cfg.settings.max_requests_queue))
            task = WorkerTask(msg_start_id, user_id, msg_id, *options)
            msg_type = MessageType.AUDIO

        except CustomError as er:
            sayOrReply(user_id, er.description)
            logger.debug(f"User ID: {user_id}\nBody {er}")
            error_description = er.code

        except Exception as er:
            sayOrReply(user_id, ErrorType.ytdlp.UNDEFINED.description)
            logger.error(f"Unexpected error: {er}")
            error_description = str(er)

        finally:
            # Запись сообщения в таблицу `vk_messages`
            vars.db.insert_message(msg_id, msg_type, user_id, msg_body, error_description)
            if task: task.vk_user_auth = vk_user_auth
            if msg_type == MessageType.PLAYLIST:
                threading.Thread(target = vars.playlist.extract_elements, args=(task,)).start()
            elif msg_type == MessageType.AUDIO:
                vars.queue.add_new_request(task)

    def listen_longpoll(self):
        """Прослушивание новых сообщений от пользователей.
        """
        logger.debug("Started.")
        self.unanswered_message_handler()
        for event in self.longpoll.listen():
            # logger.info(event.type)
            # Проверка на НОВОЕ сообщение от пользователя, а НЕ от беседы
            if event.type != VkBotEventType.MESSAGE_NEW or not event.from_user:
                continue
            msg_obj = event.obj.message
            # logger.debug(f'Получено новое сообщение: {event}')
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
