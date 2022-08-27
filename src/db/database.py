#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, psycopg2, logging, sys
from psycopg2 import Error

class DataBase():
	def __init__(self):
		self.logger = logging.getLogger('logger')

		# Инициализация объекта подключения
		self.conn = None
		self.connect_db()

	#Подключение к базе данных
	def connect_db(self):
		try:
			self.logger.debug(f'Connecting to {str(os.environ["DB_NAME"])}')
			self.conn = psycopg2.connect(
				user     = str(os.environ["PG_USER"]).strip(),
				password = str(os.environ["PG_PASSWORD"]).strip(),
				host     = str(os.environ["PG_HOST"]).strip(),
				port     = str(os.environ["PG_PORT"]).strip(),
				database = str(os.environ["DB_NAME"]).strip())
			self.conn.autocommit=True
		except (Exception, Error) as er:
			self.logger.error(f'Connection to database failed: {er}')
			self.logger.debug('Closing the program...')
			sys.exit()
		else:
			self.logger.debug('Database was connected successfully')
			self.create_tables()

	#Создание таблиц, если они отсутствуют
	def create_tables(self):
		try:
			with self.conn.cursor() as curs:
				curs.execute(open("src/db/scripts/init_tables.sql", "r").read())

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
