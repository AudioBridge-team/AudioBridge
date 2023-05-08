#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from .errorType import ErrorType

class CustomError(Exception):
    """Класс вызова настраиваемой ошибки.

    Args:
        Exception (Exception): Exception.
    """
    def __init__(self, error: ErrorType, *details):
        """Инициализация класса CustomError.

        Args:
            description (str): Описание ошибки.
            code (int): Код ошибки.
        """
        self.code = error.value
        self.description = f"Ошибка: {error.description}."
        self.details = details
