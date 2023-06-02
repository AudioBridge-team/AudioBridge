#!/usr/bin/env python3
# -*- coding: utf-8 -*-

class UserRoles:
    """Роль пользователя.
    """
    USER  : int = 1
    ADMIN : int = 2

class MessageType:
    """Тип сообщения от пользователя.
    """
    UNDEFINED    : int = 1
    PLAIN        : int = 2
    COMMAND      : int = 3
    AUDIO        : int = 4
    PLAYLIST     : int = 5
    AUDIO_RENAME : int = 6

class UserData:
    """Название поля, которое будет выбрано из таблицы users в БД.
    """
    ROLE  : str = 'role'
    TOKEN : str = 'token'

class UserSettings:
    """Название полей в таблице `user_settings`.
    """
    USER_ID      : str = 'user_id'
    IS_PROMOTING : str = 'is_promoting'
    IS_AGENT     : str = 'is_agent'

class VkAudio:
    """Название полей в таблице `vk_audio`.
    """
    AUDIO_ID       : str = 'audio_id'
    OWNER_ID       : str = 'owner_id'
    IS_SEGMENTED   : str = 'is_segmented'
    AUDIO_DURATION : str = 'audio_duration'
