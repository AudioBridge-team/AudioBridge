#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from .descriptions import *


"""Группы ошибок:
0. VkApi
1. Пользовательские
2. Группа
3. Обработчик очереди
4. Плейлист
5. Загрузчик песен
6. Ytdlp
7. Команды
"""

class ErrorType:
    userReq   : UserRequest       = UserRequest
    vkGroup   : VkGroup           = VkGroup
    queueProc : QueueProcessor    = QueueProcessor
    plProc    : PlaylistProcessor = PlaylistProcessor
    audioProc : AudioProcessor    = AudioProcessor
    ytdlp     : Ytdlp             = Ytdlp
    cmdProc   : CommandProcessor  = CommandProcessor
