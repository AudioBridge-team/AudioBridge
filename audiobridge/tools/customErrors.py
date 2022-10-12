#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
from betterconf import Config


class CustomErrorCode(Config):
	"""Типовой код настраиваемой ошибки.

	Args:
		Config (Config): Config.
	"""
	STOP_THREAD = 1

class CustomError(Exception):
	"""Класс вызова настраиваемой ошибки.

	Args:
		Exception (Exception): Exception.
	"""
	def __init__(self, text = "", code = 0):
		"""Инициализация класса CustomError.

		Args:
			text (str): Текст ошибки.
			code (int): Код ошибки.
		"""
		self.txt = text
		self.code = code

class ArgParser(argparse.ArgumentParser):
	"""Парсинг аргументов запуска программы.

	Args:
		argparse.ArgumentParser (argparse.ArgumentParser): argparse.ArgumentParser
	"""
	def error(self, message: str):
		"""Вызов настраиваемой ошибки.

		Args:
			message (str): Текст ошибки.

		Raises:
			Exception: Exception.
		"""
		raise Exception(message)
