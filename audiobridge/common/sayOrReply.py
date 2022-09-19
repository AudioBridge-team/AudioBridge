#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from vk_api.utils import get_random_id
from common.constants import vk_bot


def sayOrReply(user_id: int, _message: str, _reply_to: int = None) -> int:
	"""Функция отправки сообщения пользователя.

	Args:
		user_id (int): Идентификатор получателя (пользователя).
		_message (str): Сообщение, которое нужно отправить.
		_reply_to (int, optional): Идентификатор сообщения, на которое нужно ответить. Defaults to None.

	Returns:
		int: Идентификатор отправленного сообщения.
	"""
	if _reply_to:
		return vk_bot.messages.send(peer_id = user_id, message = _message, reply_to = _reply_to, random_id = get_random_id())
	return vk_bot.messages.send(peer_id = user_id, message = _message, random_id = get_random_id())
