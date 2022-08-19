#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse

class CustomError(Exception):
	def __init__(self, text):
		self.txt = text

class ArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        raise Exception(message)
