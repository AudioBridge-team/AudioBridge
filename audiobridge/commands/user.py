#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from .command import *
from audiobridge.config.handler import vars


class Stop(Command):
    """Общедоступная команда, которая останавляет загрузку всех песен и очищает очередь загрузки пользователя.

    Args:
        Command (_type_): Класс, описывающий структуру пользовательской команды.
    """
    def __init__(self):
        """Описание команды.
        """
        super().__init__(
            name        = "stop",
            description = "Остановить загрузку всех песен",
            category    = CommandCategory.QUEUE,
            adminOnly   = False
        )

    def run(self, *args):
        vars.queue.clear_pool(*args)
