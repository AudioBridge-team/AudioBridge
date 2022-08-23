#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import argparse
from lib2to3.pgen2.pgen import DFAState


class CustomError(Exception):
	"""Класс вызова пользовательской ошибки.

	Args:
		Exception (Exception): Exception
	"""
	def __init__(self, text):
		"""Class method docstrings go here."""
		self.txt = text

class ArgParser(argparse.ArgumentParser):
	"""Парсинг аргументов запуска программы.

	Args:
		argparse (argparse.ArgumentParser): ArgumentParser
	"""
	def error(self, message):
		raise Exception(message)
