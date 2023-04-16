#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from audiobridge.config.bot import cfg as bot_cfg


# Список всех замеченных ошибок в процессе работы yt_dlp
ytdlp_errors = {
    "is not a valid url"                                            : "Некорректный адрес источника",
    "http error 404"                                                : "Некорректный адрес источника",
    "the channel/playlist does not exist"                           : "Данный плейлист не существует",
    "is not a valid specification"                                  : "Некорректный адрес источника",
    "unable to download webpage"                                    : "Некорректный адрес источника",
    "this video was marked as adult content"                        : "VK заблокировал обработку видео из-за наличия взрослого контента",
    "unsupported url"                                               : "Данный URL не поддерживается",
    "the uploader has not made this video available in your country": "Правообладатель ограничил доступ к материалу в стране, где располагается сервер",
    "is not available in your country due to a legal complaint"     : "Из-за юридической жалобы видео недоступно в стране, в которой располагается сервер",
    "this video is not available"                                   : "Видео недоступно",
    "who has blocked it in your country on copyright"               : "Видео содержит заблокированный контент для страны, в которой располагается сервер",
    "since chapter information is unavailable"                      : "Видео не содержит эпизодов, используйте тайминги",
    "no chapters matching the regex"                                : "Данного эпизода не существует. Проверьте корректность его написания",
    "video unavailable"                                             : "Видео недоступно"
}
# Список ошибок VK API
vkapi_errors = {
    270: "Правообладатель ограничил доступ к данной аудиозаписи. Загрузка прервана",
    15 : "VK запрещает загрузку треков, вес которых меньше 50 Кб",
    100: "Невозможно загрузить аудиофайл из-за ошибки серверов VK. Повторите свой запрос чуть позже",
    10 : "Возникла непредвиденная ошибка со стороны VK. Повторите свой запрос чуть позже",
    9  : "Бот превысил лимит отправки сообщений. Повторите свой запрос через минут 30"
}
# Список прочих ошибок
specific_errors = {
    "MAX_VIDEO_DURATION": f"Суммарная продолжительность будущих аудиозаписей не может превышать {bot_cfg.settings.max_video_duration // 3600} часа!"
}

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
        self.txt  = text
        self.code = code
