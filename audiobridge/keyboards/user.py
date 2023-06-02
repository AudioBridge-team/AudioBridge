#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from vk_api.keyboard import *
from .keyboard import keys, Keyboard

from audiobridge.config.handler import vars
from audiobridge.db.dbEnums import UserSettings

from audiobridge.config.bot import cfg as bot_cfg


class Main(Keyboard):
    """Клавиатура главного меню.

    Args:
        Keyboard (Keyboard): Шаблон класса.
    """
    command: str = "main"

    def keyboard(self, *args):
        keyboard = VkKeyboard()

        keyboard.add_button("Управление очередью", color=VkKeyboardColor.PRIMARY, payload={ keys.CMD : Queue.command })
        keyboard.add_line()
        keyboard.add_button("Настройки", payload={ keys.CMD : Settings.command })
        keyboard.add_button("Прочее", payload={ keys.CMD : Other.command })

        return keyboard.get_keyboard()

class Queue(Keyboard):
    """Клавиатура меню для управления очередью запросов.

    Args:
        Keyboard (Keyboard): Шаблон класса.
    """
    command: str = "queue"

    def keyboard(self, *args):
        keyboard = VkKeyboard()

        keyboard.add_button("Пропустить", payload={ keys.CMD : "skip" })
        keyboard.add_button("Остановить", color=VkKeyboardColor.NEGATIVE, payload={ keys.CMD : "stop" })
        keyboard.add_line()
        keyboard.add_button("Назад", color=VkKeyboardColor.PRIMARY, payload={ keys.CMD : "back", keys.ARGS : [Main.command] })

        return keyboard.get_keyboard()


class Settings(Keyboard):
    """Клавиатура меню настроек.

    Args:
        Keyboard (Keyboard): Шаблон класса.
    """
    command: str = "settings"

    def keyboard(self, *args):
        keyboard = VkKeyboard()
        user_id = args[1]
        if not args[2]:
            keyboard.add_openlink_button("Авторизоваться в боте", link=(Auth.link+str(user_id)), payload={ keys.CMD : Auth.command })
        else:
            is_agent = vars.db.select_user_settings(user_id).get(UserSettings.IS_AGENT)
            if is_agent:
                keyboard.add_button("Выключить режим агента", color=VkKeyboardColor.NEGATIVE, payload={ keys.CMD : "set_agent", keys.ARGS : ["false"] })
            else:
                keyboard.add_button("Включить режим агента", color=VkKeyboardColor.POSITIVE, payload={ keys.CMD : "set_agent", keys.ARGS : ["true"] })
        keyboard.add_line()
        keyboard.add_button("Назад", color=VkKeyboardColor.PRIMARY, payload={ keys.CMD : "back", keys.ARGS : [Main.command] })

        return keyboard.get_keyboard()

class Other(Keyboard):
    """Клавиатура меню прочих функций.

    Args:
        Keyboard (Keyboard): Шаблон класса.
    """
    command: str = "other"

    def keyboard(self, *args):
        keyboard = VkKeyboard()

        keyboard.add_button("Список команд", payload={ keys.CMD : "help" })
        keyboard.add_openlink_button("Инструкция", link=Manual.link, payload={ keys.CMD : Manual.command })
        keyboard.add_line()
        keyboard.add_button("Назад", color=VkKeyboardColor.PRIMARY, payload={ keys.CMD : "back", keys.ARGS : [Main.command] })

        return keyboard.get_keyboard()

class Manual(Keyboard):
    """Виртуальная клавиатура для открытия инструкции бота.

    Args:
        Keyboard (Keyboard): Шаблон класса.
    """
    command: str = "manual"
    link   : str = "https://vk.com/saveaudio?w=page-212269992_56497954"

class Auth(Keyboard):
    """Виртуальная клавиатура для открытия страницы авторизации.

    Args:
        Keyboard (Keyboard): Шаблон класса.
    """
    command: str = "auth"
    link   : str = "\
https://oauth.vk.com/authorize?\
client_id={client_id}&\
display=page&\
redirect_uri=http://{host}:{port}&\
scope=audio,video,offline&\
response_type=code&\
v=5.131&\
state=".format(client_id = bot_cfg.authServer.app_id,
                host = bot_cfg.authServer.host,
                port = bot_cfg.authServer.port)
