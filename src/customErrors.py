#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import argparse
from lib2to3.pgen2.pgen import DFAState


class CustomError(Exception):
	"""Class docstrings go here.

	Args:
		Exception (_type_): _description_
	"""

	def __init__(self, text):
		"""Class method docstrings go here."""
		self.txt = text

class ArgParser(argparse.ArgumentParser):
	"""Class docstrings go here."""

	def error(self, message):
		"""Class method docstrings go here."""
		raise Exception(message)

