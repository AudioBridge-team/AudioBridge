#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging

from audiobridge.tools.customErrors import CustomError, ytdlp_errors

logger = logging.getLogger('logger')

class Yt_dlpShell():
    """Обработчик сообщений модуля yt_dlp.
    """
    def debug(self, msg):
        if msg.startswith('[debug] '):
            logger.debug(f"[yt-dlp] {msg}")
        else:
            self.info(msg)

    def info(self, msg):
        logger.info(f"[yt-dlp] {msg}")

    def warning(self, msg):
        logger.warning(f"[yt-dlp] {msg}")

    def error(self, msg):
        logger.error(f"[yt-dlp] {msg}")
        self.define_error_type(msg, True)

    def define_error_type(self, stderr: str, force_error = False):
        """Определение типа ошибки по ключевым словосочетаниям в теле ошибки.

        Args:
            stderr (str): Строка ошибки.
            force_error (bool, optional): Принудительный вызов ошибки, в случае если stderr не был распознал. Defaults to False.

        Raises:
            CustomError: Передача пользовательской ошибки в тело родителя данного класса.
        """
        stderr = stderr.strip().lower()
        for error_key in ytdlp_errors:
            if error_key in stderr:
                raise CustomError(f"Ошибка: {ytdlp_errors.get(error_key)}.")
        if force_error:
            raise CustomError(f"Произошла неизвестная ошибка при обработке запроса. Обратитесь к разработчикам.")
