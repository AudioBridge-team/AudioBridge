#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import locale
from datetime import date

import vk_api

from audiobridge.db.database import DataBase
from audiobridge.bot.queueHandler import QueueHandler
from audiobridge.bot.playlistHandler import PlaylistHandler
from audiobridge.bot.vkBotWorker import VkBotWorker
from audiobridge.bot.vkGroupManager import VkGroupManager
from audiobridge.tools import loggerSetup

from audiobridge.config.bot import cfg as bot_cfg
from audiobridge.config.handler import vars
from audiobridge.config.handler import Api


def main():
    """Подготовка бота к работе.
    """
    # Путь сохранения логов на удалённом сервере
    logger_path = f'../data/logs/{bot_cfg.auth.version}-{date.today()}.log'
    # Инициализация и подключение глобального logger
    logger = loggerSetup.setup('logger', logger_path)

    logger.info('Program started.')

    # Инициализация класса для подключение к базе данных
    vars.db = DataBase()

    logger.info(f'Filesystem encoding: {sys.getfilesystemencoding()}, Preferred encoding: {locale.getpreferredencoding()}')
    logger.info(f'Current version {bot_cfg.auth.version}, Bot Group ID: {bot_cfg.auth.id}')
    logger.info('Logging into VKontakte...')

    # Интерфейс для работы с аккаунтом агента (который необходим для загрузки аудио)
    m_api = Api
    vk_agent_auth        = vk_api.VkApi(token = bot_cfg.auth.agent_token)
    m_api.agent_upload = vk_api.VkUpload(vk_agent_auth)
    m_api.agent        = vk_agent_auth.get_api()

    # Интерфейс для работы с ботом
    vk_bot_auth = vk_api.VkApi(token = bot_cfg.auth.token)
    m_api.bot = vk_bot_auth.get_api()

    vars.api      = m_api
    vars.queue    = QueueHandler()
    vars.playlist = PlaylistHandler()
    vars.vk       = VkBotWorker(vk_bot_auth)

    vars.userRequests = dict()
    vkGroupManager    = VkGroupManager()

    # Запуск listener
    logger.info('Begin listening.')

    while True:
        try:
            vars.vk.listen_longpoll()
        except Exception as er:
            logger.error(f'VK API: {er}')

    logger.info('You will never see this.')


if __name__ == '__main__':
    """Точка входа в программу.
    """
    main()
