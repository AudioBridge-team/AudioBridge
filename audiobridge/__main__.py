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
from audiobridge.common import vars

from audiobridge.common.config import BotAuth

auth_conf = BotAuth()

def main():
	"""Подготовка бота к работе.
	"""
	# Версия бота
	bot_version = auth_conf.BOT_VERSION

	# Путь сохранения логов на удалённом сервере
	logger_path = f'../data/logs/{bot_version}-{date.today()}.log'
	# Инициализация и подключение глобального logger
	logger = loggerSetup.setup('logger', logger_path)

	logger.info('Program started.')

	# Подгрузка .env файла на windows
	logger.info(f'Platform is {sys.platform}')
	if sys.platform == "win32":
		from dotenv import load_dotenv
		load_dotenv()

	# Инициализация класса для подключение к базе данных
	db = DataBase()

	logger.info(f'Filesystem encoding: {sys.getfilesystemencoding()}, Preferred encoding: {locale.getpreferredencoding()}')
	logger.info(f'Current version {bot_version}, Bot Group ID: {auth_conf.BOT_ID}')
	logger.info('Logging into VKontakte...')

	# Интерфейс для работы с аккаунтом агента (который необходим для загрузки аудио)
	vk_agent_auth        = vk_api.VkApi(token = auth_conf.AGENT_TOKEN)
	vars.vk_agent_upload = vk_api.VkUpload(vk_agent_auth)
	vars.vk_agent        = vk_agent_auth.get_api()

	# Интерфейс для работы с ботом
	vk_bot_auth = vk_api.VkApi(token = auth_conf.BOT_TOKEN)
	vars.vk_bot = vk_bot_auth.get_api()

	vars.queueHandler    = QueueHandler()
	vars.playlistHandler = PlaylistHandler()
	vars.vkBotWorker     = VkBotWorker(bot_version, vk_bot_auth)

	vkGroupManager       = VkGroupManager()

	# Запуск listener
	logger.info('Begin listening.')

	while True:
		try:
			vars.vkBotWorker.listen_longpoll()
		except Exception as er:
			logger.error(f'VK API: {er}')

	logger.info('You will never see this.')


if __name__ == '__main__':
	"""Точка входа в программу.
	"""
	main()
