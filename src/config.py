#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from enum import Enum, IntEnum, auto

class Settings(IntEnum):
	MAX_WORKERS        = 6                  # максимальное число потоков для всех обработки запросов
	MAX_UNITS          = 1                  # число потоков для обработки запросов от одного пользователя
	MAX_REQUESTS_QUEUE = 5                  # максимальное кол-во запросов в общую очередь от одного пользователя

	MAX_FILESIZE       = 200 * 1024 * 1024  # максимальный размер аудио файла
	MSG_PERIOD         = 50                 # период обновления процесса загрузки файла на сервер
	MAX_VIDEO_DURATION = 3 * 60 * 60        # максимальная длительность видео в секундах
	MAX_ATTEMPTS       = 3                  # количество попыток при ошибке скачивания
	TIME_ATTEMPT       = 1                  # интервал между попытками скачивания (сек)

class RequestIndex(Enum):
	INDEX_PLAYLIST       = "/playlist"      # показатель плейлиста
	INDEX_URL            = "http" 			# показатель ссылки
	INDEX_YOUTUBE_SHORTS = "/shorts/"		# показатель YouTube Shorts

class PlaylistStates(IntEnum):
	PLAYLIST_SUCCESSFUL = auto()
	PLAYLIST_COPYRIGHT  = auto()
	PLAYLIST_UNSTATED   = auto()
