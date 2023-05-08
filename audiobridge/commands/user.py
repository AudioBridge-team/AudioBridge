#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from .command import *
from audiobridge.utils.errorHandler import *
from audiobridge.utils.sayOrReply import sayOrReply
from audiobridge.config.handler import vars

from audiobridge.db.dbEnums import UserSettings
from audiobridge.keyboards.user import Main


class Start(Command):
    name        = "start"
    description = "Ознакомиться с базовым функционалом бота"
    category    = CommandCategory.API

    def run(self, *args):
        msg = """Для того чтобы загрузить песню со сторонней площадки необходимо правильно составить запрос:
1. Ссылка на видео/песню
2. Название песни (по желанию)
3. Автор песни (по желанию)

Помимо этого вы также можете загружать целые плейлисты и конкретные отрезки из видео!
Подробнее обо всем этом вы можете ознакомиться в закреплённом посте в группе или по ссылке: vk.com/saveaudio?w=page-212269992_56497954
        """
        sayOrReply(args[0], msg, _keyboard = Main().keyboard())

class Stop(Command):
    """Общедоступная команда, которая останавляет загрузку всех песен и очищает очередь загрузки пользователя.

    Args:
        Command (_type_): Класс, описывающий структуру пользовательской команды.
    """
    name        = "stop"
    description = "Остановить загрузку всех песен"
    category    = CommandCategory.QUEUE

    def run(self, *args):
        vars.queue.clear_pool(args[0])

class Skip(Command):
    """Общедоступная команда, которая останавляет загрузку текущей песни.

    Args:
        Command (_type_): Класс, описывающий структуру пользовательской команды.
    """
    name        = "skip"
    description = "Остановить загрузку текущей песни"
    category    = CommandCategory.QUEUE

    def run(self, *args):
        vars.queue.clear_pool(args[0], True)

class SetAgent(Command):
    """Общедоступная команда, которая вкл/выкл режим агента.

    Args:
        Command (_type_): Класс, описывающий структуру пользовательской команды.
    """
    name        = "set_agent"
    description = "Включить/выключить режим агента. Команда принимает на вход 1 аргумент (true, false)"
    category    = CommandCategory.SETTINGS

    def run(self, *args):
        user_id = args[0]
        state : str = args[1]
        if not state: raise CustomError(ErrorType.cmdProc.BAD_FORMAT)
        if state[0] == "true":
            state_bool = True
            msg = "Режим агента включён"
        elif state[0] == "false":
            state_bool = False
            msg = "Режим агента выключён"
        else: raise CustomError(ErrorType.cmdProc.BAD_FORMAT)
        vars.db.set_user_setting(user_id, UserSettings.IS_AGENT, state_bool)
        sayOrReply(user_id, msg, _keyboard = Main().keyboard())
