from asyncio.log import logger
import os, psycopg2, logging, sys, json
from psycopg2 import Error

from config import PermissionsType

class DataBase():
	def __init__(self):
		self.logger = logging.getLogger('logger')

		# Инициализация объекта подключения
		self.conn = None
		self.connect_db()

		self.cache_roles()

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
			with self.conn.cursor() as curs:
				curs.execute(open("src\db\scripts\init_tables.sql", "r").read())
				curs.execute('SELECT * FROM roles')
				if not curs.fetchall():
					for user_id in json.loads(os.environ['OWNERS_ID']):
						curs.execute('INSERT INTO roles VALUES(%s, %s)', (user_id, [ PermissionsType.DEV ]))

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

	#Кеширование ролей
	def cache_roles(self):
		#Переменная для пользователей с привилегией
		self.dev_id = { }
		try:
			sql_get_id_dev = 'SELECT * FROM roles'
			with self.conn.cursor() as curs:
				curs.execute(sql_get_id_dev)
				for entry in curs.fetchall():
					if PermissionsType.DEV in entry[1]:
						self.dev_id[entry[0]] = entry[2]
		except (Exception, Error) as er:
			self.logger.error(f'Error getting dev_id: {er}')
		else:
			self.logger.debug(f'Roles were cached successfully: {self.dev_id}')

	#Получить id разработчиков
	def getDev_Id(self) -> list:
		return list(self.dev_id.keys())

	#Переключить debug режим
	def toggle_debug(self, user_id: int):
		self.dev_id[user_id] = not self.dev_id[user_id]
		try:
			sql_toggle_debug = f'UPDATE roles SET debug = %s WHERE user_id = %s'
			with self.conn.cursor() as curs:
				curs.execute(sql_toggle_debug, (self.dev_id[user_id], user_id))
		except (Exception, Error) as er:
			self.logger.error(f'Error toggle debug: {er}')
		else:
			self.logger.debug(f'{user_id} toggled debug to {self.dev_id[user_id]} successfully')

	def getUserDebugState(self, user_id: int) -> bool:
		return self.dev_id.get(user_id, False)
