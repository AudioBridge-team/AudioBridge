from asyncio.log import logger
import os, psycopg2, logging
from psycopg2 import Error
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

class DataBase():
	def __init__(self):
		logger = logging.getLogger('logger')
		# Попытка подключиться к db
		try:
			conn = psycopg2.connect(
					user     = str(os.environ["PG_USER"]),
					password = str(os.environ["PG_PASSWORD"]),
					host     = str(os.environ["PG_HOST"]),
					port     = str(os.environ["PG_PORT"]),
					database = str(os.environ["DB_NAME"]))
		except Exception as er:
			logger.error(f"Connection failed {er}")
			logger.error(f"Creating new db")
			self.create_db()
		finally:
			if conn:
				conn.close()
				logger.debug("Соединение с PostgreSQL закрыто")

		#self.sql_emulate = { 228822387: True, 160896606: True }

	def create_db(self):
		try:
			conn = psycopg2.connect(
					user     = str(os.environ["PG_USER"]),
					password = str(os.environ["PG_PASSWORD"]),
					host     = str(os.environ["PG_HOST"]),
					port     = str(os.environ["PG_PORT"]))
			conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
			cur = conn.cursor()
			cur.execute(f'CREATE DATABASE {str(os.environ["DB_NAME"])}')
		except Exception as er:
			logger.error(f'Create db error: {er}')
			if conn:
				cur.close()
				conn.close()
				logger.debug("Connection with PostgreSQL is closed")
		else:
			logger.debug(f'{str(os.environ["DB_NAME"])} was created successfully')

	def getUserDebugState(self, user_id: int) -> bool:
		return self.sql_emulate.get(user_id, False)
	def switchUserDebugState(self, user_id: int) -> bool:
		self.sql_emulate[user_id] = not self.sql_emulate[user_id]
		return self.sql_emulate.get(user_id)
	def getDevelopersId(self) -> list:
		return list(self.sql_emulate.keys())
