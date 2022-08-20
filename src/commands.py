from enum import Enum

class Commands(Enum):
	def __str__(self):
		return str(self.value)

	CLEAR = "/clear"
	VERSION = "/version"

