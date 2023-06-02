#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from vk_api.utils import get_random_id
from vk_api.keyboard import VkKeyboard
from audiobridge.config.handler import vars


def sayOrReply(user_id: int, _message: str, _reply_to: int = None, _keyboard: VkKeyboard = None) -> int:
    """Функция отправки сообщения пользователя.

    Args:
        user_id (int): Идентификатор получателя (пользователя).
        _message (str): Сообщение, которое нужно отправить.
        _reply_to (int, optional): Идентификатор сообщения, на которое нужно ответить. Defaults to None.

    Returns:
        int: Идентификатор отправленного сообщения.
    """
    return vars.api.bot.messages.send(user_id = user_id, message = _message, reply_to = _reply_to, keyboard = _keyboard, random_id = get_random_id())
