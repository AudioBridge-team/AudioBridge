#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from dataclasses import dataclass
from enum import Enum, IntEnum, auto
from environs import Env


@dataclass
class Settings:
    """Настройка работы воркера.
    """
    max_workers       : int  # Макс. число потоков для всех обработки запросов
    max_units         : int  # Число потоков для обработки запросов от одного пользователя
    max_requests_queue: int  # Макс. кол-во запросов в общую очередь от одного пользователя
    max_filesize      : int  # Макс. размер аудио файла (в байтах)
    msg_period        : int  # Период обновления прогресса скачивания трека (в сек.)
    max_video_duration: int  # Максимальная длительность видео (в сек.)
    max_attempts      : int  # Количество попыток при ошибке скачивания
    time_attempt      : int  # Интервал между попытками скачивания (в сек.)

@dataclass
class Authentication:
    """Данные авторизации бота и агента.
    """
    version    : str
    id         : int
    token      : str
    agent_token: str


class RequestIndex:
    """Показатели типа запроса.
    """
    INDEX_PLATFORM_YOUTUBE : str = "YouTube"
    INDEX_PLAYLIST         : str = "/playlist"
    INDEX_URL              : str = "http"
    INDEX_YOUTUBE_SHORTS   : str = "/shorts/"
    INDEX_VK_VIDEO         : str = "vk.com/video"

class DynamicLinksIndex(Enum):
    """Показатели динамических ссылок.

    Args:
        Enum (_type_): Dynamic link index.
    """
    SOUNDCLOUD = "on.soundcloud.com"

class PlaylistStates(IntEnum):
    """Состояние загрузки элемента из плейлиста.

    Args:
        IntEnum (IntEnum): Playlist state.
    """
    PLAYLIST_SUCCESSFUL = auto()
    PLAYLIST_COPYRIGHT  = auto()
    PLAYLIST_UNSTATED   = auto()

class CustomErrorCode(IntEnum):
    """Код причины настраиваемой ошибки.

    Args:
        IntEnum (IntEnum): Code of custom error.
    """
    STOP_THREAD = auto()  # Умышленная остановка загрузки пользователем


@dataclass
class Bot:
    settings      : Settings
    auth          : Authentication
    reqIndex      : RequestIndex
    dynLinksIndex : DynamicLinksIndex
    playlistStates: PlaylistStates
    customoErrCode: CustomErrorCode


env = Env()
env.read_env()

with open("bot_settings.json", "r", encoding="utf-8") as f:
    settings_json = json.load(f)

cfg = Bot(
    settings       = Settings(
        max_workers        = settings_json.get("max_workers", 6),
        max_units          = settings_json.get("max_units", 1),
        max_requests_queue = settings_json.get("max_requests_queue", 5),
        max_filesize       = settings_json.get("max_filesize", 200 * 1024 * 1024),
        msg_period         = settings_json.get("msg_period", 60),
        max_video_duration = settings_json.get("max_video_duration", 3 * 60 * 60),
        max_attempts       = settings_json.get("max_attempts", 3),
        time_attempt       = settings_json.get("time_attempt", 1)
    ),
    auth           = Authentication(
        version     = settings_json.get("bot_version", "v1.0.0"),
        id          = env.int('BOT_ID'),
        token       = env.str('BOT_TOKEN'),
        agent_token = env.str('AGENT_TOKEN')
    ),
    reqIndex       = RequestIndex,
    dynLinksIndex  = DynamicLinksIndex,
    playlistStates = PlaylistStates,
    customoErrCode = CustomErrorCode
)
