#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Для отслеживания кол-ва запросов от одного пользователя по MAX_REQUESTS_QUEUE
# (отрицательные значения — загрузка плейлиста, положительные — загрузка единичных песен)
userRequests = dict()

queueHandler    = None
playlistHandler = None
vkBotWorker     = None

vk_bot          = None
vk_agent        = None
vk_agent_upload = None
