#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from .command import *
from audiobridge.utils.sayOrReply import sayOrReply
from audiobridge.keyboards.user import Main
from audiobridge.config.handler import vars


class Start(Command):
    name        = "start"
    description = "Ознакомиться с базовым функционалом бота"
    category    = CommandCategory.API
    adminOnly   = False

    def run(self, *args):
        msg = """Для того чтобы загрузить песню со сторонней площадки необходимо правильно составить запрос:
1. Ссылка на видео/песню
2. Название песни (по желанию)
3. Автор песни (по желанию)

Помимо этого вы также можете загружать целые плейлисты и конкретные отрезки из видео!
Подробнее обо всем этом вы можете ознакомиться в закреплённом посте в группе или по ссылке: vk.com/saveaudio?w=page-212269992_56497954
        """
        sayOrReply(*args, msg, _keyboard=Main().keyboard())

class Stop(Command):
    """Общедоступная команда, которая останавляет загрузку всех песен и очищает очередь загрузки пользователя.

    Args:
        Command (_type_): Класс, описывающий структуру пользовательской команды.
    """
    name        = "stop"
    description = "Остановить загрузку всех песен"
    category    = CommandCategory.QUEUE
    adminOnly   = False

    def run(self, *args):
        vars.queue.clear_pool(*args)
