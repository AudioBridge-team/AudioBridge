#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import sys, os
import logging
from logging import FileHandler, Logger, StreamHandler, Formatter


def setup(logger_name: str, path: str, level=logging.DEBUG) -> Logger:
	"""Установка логгера.

	Args:
		logger_name (str): Имя логгера.
		level (logging, optional): Уровень работы логгера.. Defaults to logging.DEBUG.
	"""
	logger = logging.getLogger(logger_name)
	logger.setLevel(level)

	formatter = Formatter(
			fmt = '[%(asctime)s, %(levelname)s] ~ %(threadName)s (%(funcName)s)\t~: %(message)s',
			#fmt = '[%(asctime)s, %(levelname)s] ~ (%(funcName)s)\t~: %(message)s',
			datefmt = time.strftime('%d-%m-%y %H:%M:%S')
		)
	# Обработчик для выведения логов в консоль
	stdout_handler = StreamHandler(stream = sys.stdout)
	stdout_handler.setFormatter(formatter)

	# Создание файла, если он отсутствует
	os.makedirs(os.path.dirname(path), exist_ok=True)
	# Обработчик для сохранения логов в файл
	file_handler = FileHandler(path, mode='a')
	file_handler.setFormatter(formatter)

	logger.addHandler(stdout_handler)
	logger.addHandler(file_handler)

	return logging.getLogger('logger')
