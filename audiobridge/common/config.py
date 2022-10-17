#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from betterconf import field, Config
from betterconf.config import AbstractProvider
from betterconf.caster import to_int, AbstractCaster


class JSONProvider(AbstractProvider):
	"""Чтение конфига из json файла.

	Args:
		AbstractProvider (AbstractProvider): AbstractProvider.
	"""
	SETTINGS_JSON_FILE = "bot_settings.json"

	def __init__(self):
		"""Загрузка json файла.
		"""
		with open(self.SETTINGS_JSON_FILE, "r") as f:
			self._settings = json.load(f)

	def get(self, name: str):
		"""Получение значения по ключу

		Args:
			name (str): Ключ.

		Returns:
			Any: Значение.
		"""
		return self._settings.get(name)

class ConvertToInt(AbstractCaster):
	"""Конвертирование строки в арифметическое выражение.

	Args:
		AbstractCaster (AbstractCaster): AbstractCaster.
	"""
	def cast(self, val: str) -> int:
		"""Посчитать арифметическое выражение.

		Args:
			val (str): Арифметическое выражение.

		Returns:
			int: Результат.
		"""
		return eval(val)

class Settings(Config):
	"""Настройка работы воркера.

	Args:
		Config (Config): Config.
	"""
	MAX_WORKERS        = field("max_workers", provider=JSONProvider(), default=6) 											# максимальное число потоков для всех обработки запросов
	MAX_UNITS          = field("max_units", provider=JSONProvider(), default=1) 											# число потоков для обработки запросов от одного пользователя
	MAX_REQUESTS_QUEUE = field("max_requests_queue", provider=JSONProvider(), default=5) 									# максимальное кол-во запросов в общую очередь от одного пользователя

	MAX_FILESIZE       = field("max_filesize", caster=ConvertToInt(), provider=JSONProvider(), default=200 * 1024 * 1024) 	# максимальный размер аудио файла (в байтах)
	MSG_PERIOD         = field("msg_period", provider=JSONProvider(), default=60) 											# период отправки сообщения с прогрессом скачивания трека (в секундах)
	MAX_VIDEO_DURATION = field("max_video_duration", caster=ConvertToInt(), provider=JSONProvider(), default=3 * 60 * 60) 	# максимальная длительность видео (в секундах)
	MAX_ATTEMPTS       = field("max_attempts", provider=JSONProvider(), default=3) 											# количество попыток при ошибке скачивания
	TIME_ATTEMPT       = field("time_attempt", provider=JSONProvider(), default=1) 											# интервал между попытками скачивания (в секундах)

class BotAuth(Config):
	"""Данные авторизации бота и агента.

	Args:
		Config (Config): Config.
	"""
	BOT_ID      = field("BOT_ID", caster=to_int)
	BOT_TOKEN   = field("BOT_TOKEN")
	AGENT_TOKEN = field("AGENT_TOKEN")

class VkGroup(Config):
	"""Информация, касающаяся элементов группы

	Args:
		Config (Config): Config.
	"""
	SYNC_CHANGELOG    = field("sync_changelog", provider=JSONProvider(), default=False)
	RELEASE_UPDATE    = field("release_update", provider=JSONProvider(), default=False)
	CHANGELOG_PAGE_ID = field("CHANGELOG_PAGE_ID", caster=to_int, default=-1)

class Database(Config):
	"""Данные авторизации базы данных PostgreSql.

	Args:
		Config (Config): Config.
	"""
	DB_NAME     = field("DB_NAME")
	PG_USER     = field("PG_USER")
	PG_PASSWORD = field("PG_PASSWORD")
	PG_HOST     = field("PG_HOST")
	PG_PORT     = field("PG_PORT", caster=to_int)

class RequestIndex(Config):
	"""Показатели типа запроса.

	Args:
		Config (Config): Config.
	"""
	INDEX_PLATFORM_YOUTUBE = "YouTube"		# Показатель принадлежности видео к платформе YouTube
	INDEX_PLAYLIST         = "/playlist"    # показатель плейлиста
	INDEX_URL              = "http" 		# показатель ссылки
	INDEX_YOUTUBE_SHORTS   = "/shorts/"		# показатель YouTube Shorts
	INDEX_VK_VIDEO         = "vk.com/video"	# показатель Вк видео

class PlaylistStates(Config):
	"""Состояние загрузки элемента из плейлиста.

	Args:
		Config (Config): Config.
	"""
	PLAYLIST_SUCCESSFUL = 1
	PLAYLIST_COPYRIGHT  = 2
	PLAYLIST_UNSTATED   = 3
