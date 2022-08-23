#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from enum import Enum
class UserCommands(Enum):
	"""Команды для всех пользователей

	Args:
		Enum (Enum): список команд

	Returns:
		str: Описание команды
	"""
	HELP    = "/help",    "Вывести все команды"												#вывести все команды
	CLEAR   = "/clear",   "Остановить выполнение текущего запроса и очистить очередь"		#остановить обработку запроса и очистить очередь
	VERSION = "/version", "Узнать версию бота"												#получить официальную версию бота

	def __new__(cls, *args, **kwds):
		obj = object.__new__(cls)
		obj._value_ = args[0]
		return obj

	def __init__(self, _: str, description: str = None):
		self._description_ = description

	@property
	def description(self):
		return self._description_
