#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Команды для разработчиков
from enum import Enum

class DevCommands(Enum):
	TOGGLE   = "/toggle",   "Переключатель режима разработки"  		#переключить версию бота
	VERSIONS = "/versions", "Узнать доступные версии ботов"		#получить все доступные версии ботов

	def __new__(cls, *args, **kwds):
		obj = object.__new__(cls)
		obj._value_ = args[0]
		return obj

	def __init__(self, _: str, description: str = None):
		self._description_ = description

	@property
	def description(self):
		return self._description_
