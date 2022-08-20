from enum import Enum

#Команды для всех пользователей
class UserCommands(Enum):
	HELP 		 = "/help", "Вывести все команды"														#вывести все команды
	CLEAR        = "/clear", "Остановить выполнение текущего запроса и очистить очередь"	#остановить обработку запроса и очистить очередь
	VERSION      = "/version", "Узнать версию бота"											#получить версию бота

	def __new__(cls, *args, **kwds):
		obj = object.__new__(cls)
		obj._value_ = args[0]
		return obj

	def __init__(self, _: str, description: str = None):
		self._description_ = description

	@property
	def description(self):
		return self._description_

#Команды для разработчиков
class DevCommands(Enum):
	TOGGLE_DEBUG = "/toggle_debug", "Переключатель режима разработки"  #переключить версию бота

	def __new__(cls, *args, **kwds):
		obj = object.__new__(cls)
		obj._value_ = args[0]
		return obj

	def __init__(self, _: str, description: str = None):
		self._description_ = description

	@property
	def description(self):
		return self._description_
