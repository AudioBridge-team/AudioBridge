#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse


class CustomError(Exception):
	"""Класс вызова настраиваемой ошибки.

	Args:
		Exception (Exception): Exception.
	"""
	def __init__(self, text: str):
		"""Инициализация класса CustomError.

		Args:
			text (str): Текст ошибки.
		"""
		self.txt = text

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
