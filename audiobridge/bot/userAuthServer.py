#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import vk_api
from vk_api.utils import get_random_id

import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

from audiobridge.utils.sayOrReply import sayOrReply
from audiobridge.keyboards.user import Main
from audiobridge.config.bot import cfg as bot_cfg
from audiobridge.config.handler import vars

logger = logging.getLogger('logger')


vk_chat_url  = f"https://vk.com/write-{bot_cfg.auth.id}"
redirect_url = f"http://{bot_cfg.authServer.host}:{bot_cfg.authServer.port}"

class UserAuthServer(BaseHTTPRequestHandler):
    """Класс для поднятия веб-сервера, обрабатывающего аутентификацию пользователей.
    """
    def do_GET(self):
        """Слушатель GET запросов.
        """
        params = parse_qs(urlparse(self.path).query)
        logger.debug(f"Received GET request: {params}")
        self.send_response(302) # 302 означает, что производится временное перенаправление
        self.send_header('Location', vk_chat_url)
        self.end_headers()

        code    = params.get('code')
        user_id = params.get('state')
        if user_id and code:
            self.get_user_token(user_id[0], code[0])
        else: logger.error("Can't get code or state")

    def get_user_token(self, user_id: int, user_code: str):
        """Получение токена пользователя.

        Args:
            user_id (int): Id пользователя.
            user_code (str): User code, необходимый для получения токена.
        """
        # Клавиатура главного меню
        main_kb = Main()
        try:
            vk_user_auth  = vk_api.VkApi(app_id=bot_cfg.authServer.app_id, client_secret=bot_cfg.authServer.app_secret)
            user_auth_obj = dict(vk_user_auth.code_auth(user_code, redirect_url))
            user_token = user_auth_obj.get('access_token')
            # Запись токена в таблицу `users`
            vars.db.set_user_token(user_id, user_token)
            sayOrReply(user_id, "Вы успешно авторизовались в боте!", _keyboard = main_kb.keyboard())
        except Exception as er:
            logger.error(er)
            sayOrReply(user_id, "Ошибка: Невозможно получить токен авторизации. Обратитесь к разработчикам.", _keyboard = main_kb.keyboard())


def run_auth_service():
    """Запуск веб-сервера.
    """
    http_server = HTTPServer((bot_cfg.authServer.host, bot_cfg.authServer.port), UserAuthServer)
    logger.debug(f"Web-server started on {bot_cfg.authServer.host}:{http_server.server_port}")
    threading.Thread(target = http_server.serve_forever, name = "UserAuthServer").start()
