#!/usr/bin/env python3
# -*- coding: utf-8 -*-


CONST_NAME = "Name"


class CustomError(Exception):
	def __init__(self, text):
		self.txt = text

