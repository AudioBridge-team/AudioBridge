#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import locale
import os
from datetime import date

import vk_api

from db.database import DataBase
from bot.customErrors import ArgParser
from bot.queueHandler import QueueHandler
from bot.audioTools import AudioTools
from bot.vkBotWorker import VkBotWorker
from bot import loggerSetup
from common import constants


def main():
	# Доступные параметры запуска
	parser = ArgParser()
	parser.add_argument(
		"-v",
		"--version",
		default = "v1.0.0",
		help    = "Version of the bot")

	# Значение аргументов запуска по умолчанию
	program_version = "v1.0.0"

	# Обработка параметров запуска
	try:
		args = parser.parse_args()
	except Exception as er:
		parser.print_help()
	else:
		program_version = args.version.strip().lower()

	# Путь сохранения логов на удалённом сервере
	logger_path = f'../data/logs/{program_version}-{date.today()}.log'
	# Инициализация и подключение глобального logger
	logger = loggerSetup.setup('logger', logger_path)

	logger.info('Program started.')

	# Подгрузка .env файла на windows
	logger.info(f'Platform is {sys.platform}')
	if sys.platform == "win32":
		from dotenv import load_dotenv
		load_dotenv()

	# Инициализация класса для подключение к базе данных
	db1 = DataBase()

	logger.info(f'Filesystem encoding: {sys.getfilesystemencoding()}, Preferred encoding: {locale.getpreferredencoding()}')
	logger.info(f'Current version {program_version}, Bot Group ID: {str(os.environ["BOT_ID"]).strip()}')
	logger.info('Logging into VKontakte...')

	# Интерфейс для работы с аккаунтом агента (который необходим для загрузки аудио)
	vk_agent_auth   = vk_api.VkApi(token = str(os.environ["AGENT_TOKEN"]).strip())
	constants.vk_agent_upload = vk_api.VkUpload(vk_agent_auth)
	constants.vk_agent        = vk_agent_auth.get_api()

	# Интерфейс для работы с ботом
	vk_bot_auth = vk_api.VkApi(token = str(os.environ["BOT_TOKEN"]).strip())
	constants.vk_bot      = vk_bot_auth.get_api()

	constants.queueHandler = QueueHandler()
	constants.audioTools = AudioTools()
	constants.vkBotWorker = VkBotWorker(program_version)

	# Запуск listener
	logger.info('Begin listening.')

	while True:
		try:
			constants.vkBotWorker.listen_longpoll()
		except vk_api.exceptions.ApiError as er:
			logger.error(f'VK API: {er}')

	logger.info('You will never see this.')


if __name__ == '__main__':
	"""Точка входа в программу.
	"""
	main()
