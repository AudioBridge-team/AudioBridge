#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from environs import Env
from dataclasses import dataclass


@dataclass
class Database:
    """Данные авторизации базы данных PostgreSql.
    """
    name    : str
    user    : str
    password: str
    host    : str
    port    : int


env = Env()
env.read_env()

cfg = Database(
    name     = env.str('DB_NAME'),
    user     = env.str('PG_USER'),
    password = env.str('PG_PASSWORD'),
    host     = env.str('PG_HOST'),
    port     = env.int('PG_PORT')
)
