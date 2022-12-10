#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from betterconf import Config
from audiobridge.common.config import Settings


settings_conf = Settings()
# Список всех замеченных ошибок в процессе работы yt_dlp
ytdlp_errors = {
	"is not a valid url"                                            : "Некорректный адрес источника",
	"http error 404"                                                : "Некорректный адрес источника",
	"the channel/playlist does not exist"                           : "Данный плейлист не существует",
	"is not a valid specification"                                  : "Некорректный адрес источника",
	"http error 404"                                                : "Неверные параметры скачивания плейлиста",
	"unable to download webpage"                                    : "Некорректный адрес источника",
	"video unavailable"                                             : "Видео недоступно",
	"this video was marked as adult content"                        : "VK заблокировал обработку видео из-за наличия взрослого контента",
	"unsupported url"                                               : "Данный URL не поддерживается",
	"the uploader has not made this video available in your country": "Правообладатель ограничил доступ к материалу в данной стране",
	"this video is not available"                                   : "Видео недоступно",
	"who has blocked it in your country on copyright"               : "Видео содержит заблокированный для нашей страны контент",
	"since chapter information is unavailable"                      : "Видео не содержит эпизодов, используйте тайминги",
	"no chapters matching the regex"                                : "Данного эпизода не существует. Проверьте корректность его написания"
}
# Список прочих ошибок
specific_errors = {
	"MAX_VIDEO_DURATION": f"Суммарная продолжительность будущих аудиозаписей не может превышать {settings_conf.MAX_VIDEO_DURATION} часа!"
}

class CustomErrorCode(Config):
	"""Код причины настраиваемой ошибки.

	Args:
		Config (Config): Config.
	"""
	STOP_THREAD = 1 # Умышленная остановка загрузки пользователем

class CustomError(Exception):
	"""Класс вызова настраиваемой ошибки.

	Args:
		Exception (Exception): Exception.
	"""
	def __init__(self, text = "", code = 0):
		"""Инициализация класса CustomError.

		Args:
			text (str): Текст ошибки.
			code (int): Код ошибки.
		"""
		self.txt = text
		self.code = code
