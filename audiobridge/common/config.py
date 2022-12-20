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

class ParametersType(Config):
	MSG_START   = 0  # id сообщения с добавлением запроса в очередь пользователя
	USER_ID     = 1  # id пользователя
	MSG_REPLY   = 2  # id сообщения запроса пользователя
	URL         = 3  # Ссылка на песню
	SONG_NAME   = 4  # Название песни
	SONG_AUTHOR = 5  # Автор песни
	INTERVAL    = 6  # Временной интервал
	PL_PARAM    = 7  # Кол-во загружаемых видео, если запрос — плейлист
	PL_TYPE     = 8  # Если True, то запрос является плейлистом
	PL_ELEMENT  = 9  # Порядковый номер элемента в плейлисте
	PL_SIZE     = 10 # Размер плейлиста

class Settings(Config):
	"""Настройка работы воркера.

	Args:
		Config (Config): Config.
	"""
	# Максимальное число потоков для всех обработки запросов
	MAX_WORKERS        = field("max_workers", provider=JSONProvider(), default=6)
	# Число потоков для обработки запросов от одного пользователя
	MAX_UNITS          = field("max_units", provider=JSONProvider(), default=1)
	# Максимальное кол-во запросов в общую очередь от одного пользователя
	MAX_REQUESTS_QUEUE = field("max_requests_queue", provider=JSONProvider(), default=5)

	# Максимальный размер аудио файла (в байтах)
	MAX_FILESIZE       = field("max_filesize", caster=ConvertToInt(), provider=JSONProvider(), default=200 * 1024 * 1024)
	# Период отправки сообщения с прогрессом скачивания трека (в секундах)
	MSG_PERIOD         = field("msg_period", provider=JSONProvider(), default=60)
	# Максимальная длительность видео (в секундах)
	MAX_VIDEO_DURATION = field("max_video_duration", caster=ConvertToInt(), provider=JSONProvider(), default=3 * 60 * 60)
	# Количество попыток при ошибке скачивания
	MAX_ATTEMPTS       = field("max_attempts", provider=JSONProvider(), default=3)
	# Интервал между попытками скачивания (в секундах)
	TIME_ATTEMPT       = field("time_attempt", provider=JSONProvider(), default=1)

class BotAuth(Config):
	"""Данные авторизации бота и агента.

	Args:
		Config (Config): Config.
	"""
	BOT_VERSION = field("bot_version", provider=JSONProvider(), default="v1.0.0")
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
	INDEX_PLATFORM_YOUTUBE = "YouTube"      # Показатель принадлежности видео к платформе YouTube
	INDEX_PLAYLIST         = "/playlist"    # Показатель плейлиста
	INDEX_URL              = "http"         # Показатель ссылки
	INDEX_YOUTUBE_SHORTS   = "/shorts/"     # Показатель YouTube Shorts
	INDEX_VK_VIDEO         = "vk.com/video" # Показатель Вк видео

class PlaylistStates(Config):
	"""Состояние загрузки элемента из плейлиста.

	Args:
		Config (Config): Config.
	"""
	PLAYLIST_SUCCESSFUL = 1
	PLAYLIST_COPYRIGHT  = 2
	PLAYLIST_UNSTATED   = 3
