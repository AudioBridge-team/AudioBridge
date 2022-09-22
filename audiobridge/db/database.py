#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import os, sys
from os.path import realpath
import psycopg2
from psycopg2 import Error


logger = logging.getLogger('logger')

class DataBase():
	"""Интерфейс для работы с базой данных PostgreSql.
	"""

	def __init__(self):
		"""Инициализация класса DataBase.
		"""
		logger = logging.getLogger('logger')

		# Инициализация объекта подключения
		self.conn = None
		self.connect_db()

	#Подключение к базе данных
	def connect_db(self):
		"""Подключение к базе данных.
		"""
		try:
			logger.debug(f'Connecting to {str(os.environ["DB_NAME"])}')
			self.conn = psycopg2.connect(
				user     = str(os.environ["PG_USER"]).strip(),
				password = str(os.environ["PG_PASSWORD"]).strip(),
				host     = str(os.environ["PG_HOST"]).strip(),
				port     = str(os.environ["PG_PORT"]).strip(),
				database = str(os.environ["DB_NAME"]).strip())
			self.conn.autocommit=True
		except (Exception, Error) as er:
			logger.error(f'Connection to database failed: {er}')
			logger.debug('Closing the program...')
			sys.exit()
		else:
			logger.debug('Database was connected successfully')
			self.create_tables()

	#Создание таблиц, если они отсутствуют
	def create_tables(self):
		"""Создание необходимых таблиц в случае их отсутствия.
		"""
		try:
			path_dir = os.path.dirname(__file__)
			with self.conn.cursor() as curs:
				curs.execute(open(realpath(path_dir + "/scripts/init_tables.sql"), "r").read())

		except (Exception, Error) as er:
			#Закрытие освобождение памяти + выход из программы для предотвращения рекурсии и настройки PostgreSQL на хосте
			logger.error(f'Tables creation failed: {er}')
			if self.conn:
				self.conn.close()
				logger.debug('Connection was closed')
			logger.debug('Closing the program...')
			sys.exit()
		else:
			logger.debug(f'Tables are ready to use')
