#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
from audiobridge.config.handler import vars


logger = logging.getLogger('logger')

def deleteMsg(msg_id: int):
    """Функция удаления сообщения в чате с пользователем.

    Args:
        msg_id (int): id сообщения, которое нужно удалить.
    """
    if not msg_id: return
    try:
        vars.api.bot.messages.delete(delete_for_all = 1, message_ids = msg_id)
    except Exception as er:
        logger.warning(f"Can't delete message:\n{er}")
