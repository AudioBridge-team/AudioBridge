#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from enum import Enum, IntEnum, auto

class Settings(IntEnum):
	"""Настройка работы воркера.

	Args:
		IntEnum (IntEnum): IntEnum.
	"""
	MAX_WORKERS        = 6                  # максимальное число потоков для всех обработки запросов
	MAX_UNITS          = 1                  # число потоков для обработки запросов от одного пользователя
	MAX_REQUESTS_QUEUE = 5                  # максимальное кол-во запросов в общую очередь от одного пользователя

	MAX_FILESIZE       = 200 * 1024 * 1024  # максимальный размер аудио файла
	MSG_PERIOD         = 50                 # период обновления процесса загрузки файла на сервер
	MAX_VIDEO_DURATION = 3 * 60 * 60        # максимальная длительность видео в секундах
	MAX_ATTEMPTS       = 3                  # количество попыток при ошибке скачивания
	TIME_ATTEMPT       = 1                  # интервал между попытками скачивания (сек)

class RequestIndex(Enum):
	"""Показатели типа запроса.

	Args:
		Enum (Enum): Enum.
	"""
	INDEX_PLAYLIST       = "/playlist"      # показатель плейлиста
	INDEX_URL            = "http" 			# показатель ссылки
	INDEX_YOUTUBE_SHORTS = "/shorts/"		# показатель YouTube Shorts
	INDEX_VK_VIDEO       = "vk.com/video"	# показатель Вк видео

class PlaylistStates(IntEnum):
	"""Состояние загрузки элемента из плейлиста.

	Args:
		IntEnum (IntEnum): IntEnum.
	"""
	PLAYLIST_SUCCESSFUL = auto()
	PLAYLIST_COPYRIGHT  = auto()
	PLAYLIST_UNSTATED   = auto()
