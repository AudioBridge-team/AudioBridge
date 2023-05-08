#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import sys
from os.path import realpath, dirname
import psycopg2
from psycopg2 import Error, IntegrityError
from psycopg2 import sql

from audiobridge.utils.errorHandler import *
from audiobridge.config.db import cfg as db_cfg
from .dbEnums import UserRoles, UserSettings

logger = logging.getLogger('logger')

class Database():
    """Интерфейс для работы с базой данных PostgreSql.
    """
    def __init__(self):
        """Инициализация класса Database.
        """
        # Инициализация объекта подключения
        self.conn = None
        self.connect_db()

    #Подключение к базе данных
    def connect_db(self):
        """Подключение к базе данных.
        """
        try:
            logger.debug(f"Connecting to {db_cfg.name}")
            self.conn = psycopg2.connect(
                user     = db_cfg.user,
                password = db_cfg.password,
                host     = db_cfg.host,
                port     = db_cfg.port,
                database = db_cfg.name)
            self.conn.autocommit=True
        except (Exception, Error) as er:
            logger.error(f"Connection to database failed: {er}")
            logger.debug("Closing the program...")
            sys.exit()
        else:
            logger.debug("Database was connected successfully")
            self.init_scripts()

    #Создание таблиц, если они отсутствуют
    def init_scripts(self):
        """Создание необходимых таблиц в случае их отсутствия.
        """
        try:
            with self.conn.cursor() as curs:
                curs.execute(open(realpath(dirname(__file__) + "/scripts/init_tables.sql"), "r", encoding="utf-8").read())
                curs.execute(open(realpath(dirname(__file__) + "/scripts/init_triggers.sql"), "r", encoding="utf-8").read())

        except (Exception, Error) as er:
            #Закрытие освобождение памяти + выход из программы для предотвращения рекурсии и настройки PostgreSQL на хосте
            logger.error(f"Script initialization failed: {er}")
            if self.conn:
                self.conn.close()
                logger.debug("Connection was closed")
            logger.debug("Closing the program...")
            sys.exit()
        else:
            logger.debug(f"Database is ready to use")

    def insert_message(self, *values):
        """Добавление нового сообщения от пользователя в БД.

        Args:
            values (*args): Значения запроса (msg_id, msg_type, author_id, msg_body, error_description).
        """
        values = tuple(filter(None, values))
        try:
            var_placeholders = sql.SQL(', ').join(sql.Placeholder() * len(values))
            insert_query = sql.SQL("INSERT INTO vk_messages VALUES ({})").format(var_placeholders)
            with self.conn.cursor() as curs:
                curs.execute(insert_query, values)

        except Error as er:
            logger.error(f"Code: {er.pgcode}\nBody: {er}")
            if er.pgcode == '23503':
                self._insert_user(values[2])
                logger.debug("Trying to insert message again...")
                self.insert_message(*values)
        except Exception as er:
            logger.error(f"Unexpected error: {er}")
        else:
            logger.debug("Message has been successfully inserted")

    def set_error_code(self, msg_id, error_description):
        """Установка ошибки обработки сообщения.

        Args:
            msg_id (_type_): Id сообщения.
            error_description (_type_): Описание ошибки.
        """
        try:
            insert_query = sql.SQL("UPDATE vk_messages SET error_description = %s WHERE msg_id = %s")
            with self.conn.cursor() as curs:
                curs.execute(insert_query, (error_description, msg_id,))

        except Error as er:
            logger.error(f"Code: {er.pgcode}\nBody :{er}")
        except Exception as er:
            logger.error(f"Unexpected error: {er}")
        else:
            logger.debug(f"Error description has been successfully set")

    def _insert_user(self, user_id: int, user_role : UserRoles = UserRoles.USER):
        """Добавление нового пользователя в БД.

        Args:
            user_id (int): Id пользователя.
        """
        try:
            insert_query = sql.SQL("INSERT INTO users VALUES (%s, %s)")
            with self.conn.cursor() as curs:
                curs.execute(insert_query, (user_id, user_role,))

        except Error as er:
            logger.error(f"Code: {er.pgcode}\nBody :{er}")
        except Exception as er:
            logger.error(f"Unexpected error: {er}")
        else:
            logger.debug(f"User has been successfully added")

    def set_user_token(self, user_id: int, token: str):
        """Установка токена пользователя.

        Args:
            user_id (int): Id пользователя.
            token (str)  : Токен пользователя.
        """
        try:
            insert_query = sql.SQL("UPDATE users SET token = %s WHERE user_id = %s")
            with self.conn.cursor() as curs:
                curs.execute(insert_query, (token, user_id,))

        except Error as er:
            logger.error(f"Code: {er.pgcode}\nBody :{er}")
        except Exception as er:
            logger.error(f"Unexpected error: {er}")
        else:
            logger.debug(f"User token has been successfully set")

    def select_user_data(self, user_id: int) -> dict:
        """Получение определённой информации пользователя.

        Args:
            user_id (int): Id пользователя.

        Returns:
            int: Информация о пользователе.
        """
        values  = tuple()
        columns = list()
        try:
            insert_query = sql.SQL("SELECT * FROM users WHERE user_id = %s")
            with self.conn.cursor() as curs:
                curs.execute(insert_query, (user_id,))
                values = curs.fetchone()
                columns = list(curs.description)

        except Error as er:
            logger.error(f"Can't get user data\nCode: {er.pgcode}\nBody :{er}")
        except Exception as er:
            logger.error(f"Unexpected error: {er}")
        else:
            logger.debug(f"User data has been successfully selected")

        res = {}
        if not values: return res
        for i, col in enumerate(columns):
            res[col.name] = values[i]
        return res

    def set_user_setting(self, user_id: int, setting_type: UserSettings, setting_value: bool):
        """Установка конкретной настройки пользователя.

        Args:
            user_id (int): Id пользователя.
            setting_type (UserSettings): Тип настройки.
            setting_value (bool): Значение настройки.
        """
        try:
            insert_query = sql.SQL("UPDATE user_settings SET {} = %s WHERE user_id = %s").format(sql.Identifier(setting_type))
            with self.conn.cursor() as curs:
                curs.execute(insert_query, (setting_value, user_id,))

        except Error as er:
            logger.error(f"Can't set user {setting_type}\nCode: {er.pgcode}\nBody :{er}")
            if er.pgcode == 'P0001' and setting_type == UserSettings.IS_AGENT:
                raise CustomError(ErrorType.cmdProc.NO_TOKEN)
        except Exception as er:
            logger.error(f"Unexpected error: {er}")
        else:
            logger.debug(f"User {setting_type} has been successfully set")

    def select_user_settings(self, user_id: int) -> dict:
        """Выбор настроек пользователя.

        Args:
            user_id (int): Id пользователя.

        Returns:
            dict: Настроки пользователя.
        """
        values  = tuple()
        columns = list()
        try:
            insert_query = sql.SQL("SELECT * FROM user_settings WHERE user_id = %s")
            with self.conn.cursor() as curs:
                curs.execute(insert_query, (user_id,))
                values = curs.fetchone()
                columns = list(curs.description)

        except Error as er:
            logger.error(f"Can't get user settings\nCode: {er.pgcode}\nBody :{er}")
        except Exception as er:
            logger.error(f"Unexpected error: {er}")
        else:
            logger.debug(f"User settings has been successfully selected: {values}")

        res = {}
        for i, col in enumerate(columns):
            res[col.name] = values[i]
        return res

    def init_convert_request(self, msg_request_id: int, download_url: str) -> int:
        """Добавление в таблицу convert_requests основных полей

        Args:
            msg_request_id (int): id сообщения с запросом
            download_url (str): url загружаемой песни
        """
        task_id : int = None
        try:
            insert_query = sql.SQL("INSERT INTO convert_requests (msg_request_id, download_url) VALUES (%s, %s) RETURNING task_id")
            with self.conn.cursor() as curs:
                curs.execute(insert_query, (msg_request_id, download_url,))
                res = curs.fetchone()
                if res: task_id = res[0]

        except Error as er:
            logger.error(f"Code: {er.pgcode}\nBody: {er}")
        except Exception as er:
            logger.error(f"Unexpected error: {er}")
        else:
            logger.debug("Convert request has been successfully initializated in db")
        return task_id

    def complete_convert_request(self, task_id: int, values: dict):
        """Помещает в convert_request оставшиеся данные обработки запроса.

        Args:
            task_id (int): id записи в бд.
            values (dict): Значения запроса (audio_id, error_description, process_time).
        """
        try:
            var_identifiers = sql.SQL(', ').join(map(sql.Identifier, values.keys()))
            var_placeholders = sql.SQL(', ').join(sql.Placeholder() * len(values))
            insert_query = sql.SQL("UPDATE convert_requests SET ({}) = ({}) WHERE task_id = %s").format(var_identifiers, var_placeholders)
            with self.conn.cursor() as curs:
                curs.execute(insert_query, list(values.values()) + [task_id])

        except Error as er:
            logger.error(f"Code: {er.pgcode}\nBody :{er}")
        except Exception as er:
            logger.error(f"Unexpected error: {er}")
        else:
            logger.debug(f"Convert request has been successfully completed")

    def insert_audio(self, values: dict) -> bool:
        """Добавление загруженной песни в базу данных.

        Args:
            values (dict): Значения запроса (audio_id, is_segmented, audio_duration).

        Returns:
            int: id загруженной песни.
        """
        status = False
        try:
            var_identifiers = sql.SQL(', ').join(map(sql.Identifier, values.keys()))
            var_placeholders = sql.SQL(', ').join(sql.Placeholder() * len(values))
            insert_query = sql.SQL("INSERT INTO vk_audio ({}) VALUES ({})").format(var_identifiers, var_placeholders)
            with self.conn.cursor() as curs:
                curs.execute(insert_query, list(values.values()))

        except Error as er:
            logger.error(f"Code: {er.pgcode}\nBody :{er}")
        except Exception as er:
            logger.error(f"Unexpected error: {er}")
        else:
            status = True
            logger.debug(f"Audio has been successfully inserted")
        return status

    def select_original_audio(self, download_url: str) -> tuple:
        """Выбор объекта песни, ранее загруженной в вк.

        Args:
            download_url (str): Ссылка, соответствующая данной песни.

        Returns:
            tuple: Объект песни.
        """
        audio_obj = tuple()
        try:
            query_audio_id = "SELECT DISTINCT ON (audio_id) audio_id FROM convert_requests WHERE (audio_id IS NOT NULL) and (download_url = %s)"
            insert_query = sql.SQL("SELECT * FROM vk_audio WHERE (NOT is_segmented) and (audio_id = ({}))").format(sql.SQL(query_audio_id))
            with self.conn.cursor() as curs:
                curs.execute(insert_query, (download_url,))
                audio_obj = curs.fetchone()

        except Error as er:
            logger.error(f"Can't get audio\nCode: {er.pgcode}\nBody :{er}")
        except Exception as er:
            logger.error(f"Unexpected error: {er}")
        else:
            logger.debug(f"Audio object has been successfully selected: {audio_obj}")
        return audio_obj
