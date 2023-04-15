#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import subprocess
from audiobridge.utils.customErrors import CustomError

from audiobridge.config.bot import cfg as bot_cfg
from audiobridge.config.vkGroup import cfg as vkgroup_cfg
from audiobridge.config.handler import vars


logger = logging.getLogger('logger')

class VkGroupManager():
    """Управление группой Вк.
    """
    def __init__(self):
        """Инициализация класса VkGroupManager.
        """
        logger.info(f'Synchronize vk changelog is: {vkgroup_cfg.sync_changelog}')
        logger.info(f'Release vk post-update is: {vkgroup_cfg.release_update}')
        if vkgroup_cfg.sync_changelog:
            self._sync_changelog()

    def _fix_wiki_for_vk(self, wiki: str) -> str:
        """Доработка wiki формата под стилистику wiki-страниц Вк.

        Args:
            wiki (str): Переведенный текст из .md формата в .wiki формат.

        Returns:
            str: Доработанный текст под стилистику wiki-страниц Вк.
        """
        fixed_wiki = ""
        for line in wiki.splitlines(True):
            if line.startswith('='):
                line = '=' + line.strip() + '='
                if "Unreleased" in line:
                    line += '\n'
            if '[' in line and ']' in line:
                last_pos = 0
                while last_pos != -1:
                    last_pos = line.find('[', last_pos+1)
                    if last_pos != -1:
                        pos = line.find(' ', last_pos)
                        line = line[:pos] + '|' + line[pos+1:]
            fixed_wiki += line
        return fixed_wiki

    def _sync_changelog(self):
        """Синхронизация локального CHANGELOG.md с wiki-страницей в вк.

        Raises:
            CustomError: Вызов ошибки с настраиваемым содержанием.
        """
        try:
            if vkgroup_cfg.changelog_page_id == -1:
                raise CustomError("Changelog page id isn't set. Changelog wasn't synchronized!")

            proc = subprocess.Popen("pandoc CHANGELOG.md -t mediawiki", stdout = subprocess.PIPE, stderr = subprocess.PIPE, text = True, shell = True)
            stdout, stderr = proc.communicate()
            if stderr:
                raise CustomError(f"Can't convert .md to .wiki: {stderr}")
            if not stdout:
                raise CustomError('CHANGELOG.wiki is empty!')

            vars.api.agent.pages.save(text=self._fix_wiki_for_vk(stdout), page_id=vkgroup_cfg.changelog_page_id, group_id=bot_cfg.auth.id)
            logger.debug("Changelog was synchronized successfully!")
            if vkgroup_cfg.release_update:
                logger.debug("Releasing post with new update...")

        except CustomError as er:
            logger.error(f'Custom: {er}')
        except Exception as er:
            logger.error(f"Can't update vk changelog: {er}")
