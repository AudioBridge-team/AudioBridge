class DataBase():
	def __init__(self):
		self.sql_emulate = { 228822387: True, 160896606: True }

	def getUserDebugState(self, user_id: int) -> bool:
		return self.sql_emulate.get(user_id, False)

	def switchUserDebugState(self, user_id: int) -> bool:
		self.sql_emulate[user_id] = not self.sql_emulate[user_id]
		return self.sql_emulate.get(user_id)

	def getDevelopersId(self) -> list:
		return list(self.sql_emulate.keys())
