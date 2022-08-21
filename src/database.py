import os, psycopg2, logging, sys
from psycopg2 import Error

class DataBase():
	def __init__(self):
		self.logger = logging.getLogger('logger')
		self.sql_emulate = { 228822387: True, 160896606: True }
		# Инициализация объекта подключения
		self.conn = None
		# Попытка подключиться к db
		self.connect_db()

	#Подключение к базе данных
	def connect_db(self):
		try:
			self.logger.debug(f'Connecting to {str(os.environ["DB_NAME"])}')
			self.conn = psycopg2.connect(
				user     = str(os.environ["PG_USER"]),
				password = str(os.environ["PG_PASSWORD"]),
				host     = str(os.environ["PG_HOST"]),
				port     = str(os.environ["PG_PORT"]),
				database = str(os.environ["DB_NAME"]))
			self.conn.autocommit=True
		except (Exception, Error) as er:
			self.logger.error(f'Connection failed {er}')
			#Создание базы данных в случае её отсутствия
			self.create_db()
		else:
			self.logger.debug('Database was connected successfully')
			self.create_tables()

	#Создание базы данных
	def create_db(self):
		try:
			self.logger.debug(f'Creating {str(os.environ["DB_NAME"])}')
			self.conn = psycopg2.connect(
				user     = str(os.environ["PG_USER"]),
				password = str(os.environ["PG_PASSWORD"]),
				host     = str(os.environ["PG_HOST"]),
				port     = str(os.environ["PG_PORT"]))
			self.conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)

			sql_create_db = f'CREATE DATABASE {str(os.environ["DB_NAME"])}'
			with self.conn.cursor() as curs:
				curs.execute(sql_create_db)

		except (Exception, Error) as er:
			#Закрытие освобождение памяти + выход из программы для предотвращения рекурсии и настройки PostgreSQL на хосте
			self.logger.error(f'Db creation failed: {er}')
			if self.conn:
				self.conn.close()
				self.logger.debug('Connection was closed')
			self.logger.debug('Closing the program...')
			sys.exit()
		else:
			self.logger.debug(f'Database was created successfully')
			#Повторное подключение к базе данных
			self.connect_db()

	#Создание таблиц, если они отсутствуют
	def create_tables(self):
		try:
			sql_create_table_roles = '''
				CREATE TABLE if not exists roles (
					user_id INTEGER PRIMARY KEY,
					roles TEXT DEFAULT 'admin'
				);
			'''
			sql_create_table_requests = '''
				CREATE TABLE if not exists audio_requests (
					user_id INTEGER PRIMARY KEY,
					audio_id TEXT UNIQUE,
					audio_url TEXT NOT NULL,
					audio_name TEXT,
					audio_author TEXT,
					audio_segment TEXT,
					date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
				);
			'''

			with self.conn.cursor() as curs:
				curs.execute(sql_create_table_roles)
				curs.execute(sql_create_table_requests)

		except (Exception, Error) as er:
			#Закрытие освобождение памяти + выход из программы для предотвращения рекурсии и настройки PostgreSQL на хосте
			self.logger.error(f'Tables creation failed: {er}')
			if self.conn:
				self.conn.close()
				self.logger.debug('Connection was closed')
			self.logger.debug('Closing the program...')
			sys.exit()
		else:
			self.logger.debug(f'Tables are ready to use')


	def getUserDebugState(self, user_id: int) -> bool:
		return self.sql_emulate.get(user_id, False)
	def switchUserDebugState(self, user_id: int) -> bool:
		self.sql_emulate[user_id] = not self.sql_emulate[user_id]
		return self.sql_emulate.get(user_id)
	def getDevelopersId(self) -> list:
		return list(self.sql_emulate.keys())
