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

@dataclass
class UserAuthServer:
    """Данные для запуска веб-сервера, обрабатываюзего авторизацию пользователей, и вк мини-апп.
    """
    app_id     : int
    app_secret : str
    host       : str
    port       : int

class DynamicLinksIndex(Enum):
    """Показатели динамических ссылок.

    Args:
        Enum (_type_): Dynamic link index.
    """
    SOUNDCLOUD = "on.soundcloud.com"

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


@dataclass
class Bot:
    settings      : Settings
    auth          : Authentication
    authServer    : UserAuthServer
    dynLinksIndex : DynamicLinksIndex
    playlistStates: PlaylistStates


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
    authServer     = UserAuthServer(
        app_id     = env.int('APP_ID'),
        app_secret = env.str('APP_SECRET'),
        host       = env.str('SERVER_HOST'),
        port       = env.int('SERVER_PORT'),
    ),
    dynLinksIndex  = DynamicLinksIndex,
    playlistStates = PlaylistStates
)
