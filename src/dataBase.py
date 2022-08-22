#!/usr/bin/env python3
# -*- coding: utf-8 -*-


class DataBase():
	"""Class docstrings go here."""

	def __init__(self):
		"""Class method docstrings go here."""
		self.sql_emulate = { 228822387: True, 160896606: True }

	def getUserDebugState(self, user_id: int) -> bool:
		"""Class method docstrings go here."""
		return self.sql_emulate.get(user_id, False)

	def switchUserDebugState(self, user_id: int) -> bool:
		"""Class method docstrings go here."""
		self.sql_emulate[user_id] = not self.sql_emulate[user_id]
		return self.sql_emulate.get(user_id)

	def getDevelopersId(self) -> list:
		"""Class method docstrings go here."""
		return list(self.sql_emulate.keys())

