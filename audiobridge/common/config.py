#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from betterconf import field, Config
from betterconf.config import AbstractProvider
from betterconf.caster import AbstractCaster


class JSONProvider(AbstractProvider):
    SETTINGS_JSON_FILE = "bot_settings.json"

    def __init__(self):
        with open(self.SETTINGS_JSON_FILE, "r") as f:
            self._settings = json.load(f)

    def get(self, name):
        return self._settings.get(name)

class ConvertToInt(AbstractCaster):
    def cast(self, val: str):
        return eval(val)

class Settings(Config):
	"""Настройка работы воркера.

	Args:
		IntEnum (IntEnum): IntEnum.
	"""
	MAX_WORKERS        = field("max_workers", provider=JSONProvider(), default=6) 											# максимальное число потоков для всех обработки запросов
	MAX_UNITS          = field("max_units", provider=JSONProvider(), default=1) 											# число потоков для обработки запросов от одного пользователя
	MAX_REQUESTS_QUEUE = field("max_requests_queue", provider=JSONProvider(), default=5) 									# максимальное кол-во запросов в общую очередь от одного пользователя

	MAX_FILESIZE       = field("max_filesize", caster=ConvertToInt(), provider=JSONProvider(), default=200 * 1024 * 1024) 	# максимальный размер аудио файла
	MSG_PERIOD         = field("msg_period", provider=JSONProvider(), default=50) 											# период обновления процесса загрузки файла на сервер
	MAX_VIDEO_DURATION = field("max_video_duration", caster=ConvertToInt(), provider=JSONProvider(), default=3 * 60 * 60) 	# максимальная длительность видео в секундах
	MAX_ATTEMPTS       = field("max_attempts", provider=JSONProvider(), default=3) 											# количество попыток при ошибке скачивания
	TIME_ATTEMPT       = field("time_attempt", provider=JSONProvider(), default=1) 											# интервал между попытками скачивания (сек)

class RequestIndex(Config):
	"""Показатели типа запроса.

	Args:
		Enum (Enum): Enum.
	"""
	INDEX_PLAYLIST       = "/playlist"      # показатель плейлиста
	INDEX_URL            = "http" 			# показатель ссылки
	INDEX_YOUTUBE_SHORTS = "/shorts/"		# показатель YouTube Shorts
	INDEX_VK_VIDEO       = "vk.com/video"	# показатель Вк видео

class PlaylistStates(Config):
	"""Состояние загрузки элемента из плейлиста.

	Args:
		IntEnum (IntEnum): IntEnum.
	"""
	PLAYLIST_SUCCESSFUL = 1
	PLAYLIST_COPYRIGHT  = 2
	PLAYLIST_UNSTATED   = 3
