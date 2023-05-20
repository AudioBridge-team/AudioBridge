#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import os
import threading, subprocess
import time

import yt_dlp

import vk_api
from vk_api.utils import get_random_id

from audiobridge.utils.errorHandler import *

from audiobridge.utils.sayOrReply import sayOrReply
from audiobridge.utils.deleteMsg import deleteMsg
from audiobridge.utils.yt_dlpShell import Yt_dlpShell

from audiobridge.config.bot import cfg as bot_cfg
from audiobridge.config.handler import vars, WorkerTask
from audiobridge.db.dbEnums import UserSettings, VkAudio


logger      = logging.getLogger('logger')
yt_dlpShell = Yt_dlpShell()

# Команда для получения битрейта аудио
cmdAudioBitrate = lambda url: 'ffmpeg -loglevel info -hide_banner -i "{0}"'.format(f"$(yt-dlp --no-playlist --no-warnings -x -g '{url}')")

ydl_opts = {
    'logger': yt_dlpShell,
    'nocheckcertificate': True,
    'retries': bot_cfg.settings.max_attempts,
    'format': 'bestaudio/best',
    'noplaylist': True
}

class AudioWorker(threading.Thread):
    """Аудио воркер — класс скачивания песен и загрузки в Вк.

    Args:
        threading.Thread (threading.Thread): threading.Thread

    Raises:
        CustomError: Вызов ошибки с настраиваемым содержанием.
    """
    def __init__(self, task: WorkerTask):
        """Инициализация класса AudioWorker.

        Args:
            task (list): Пользовательский запрос.
        """
        super(AudioWorker, self).__init__()

        self._stop       = False
        self.msg_start   = task.msg_start    # id сообщения с размером очереди (необходимо для удаления в конце обработки запроса)
        self.user_id     = task.user_id
        self.msg_reply   = task.msg_reply    # id сообщения пользователя (необходимо для ответа на него)
        self.url         = task.url
        self.song_name   = task.song_name
        self.song_author = task.song_author
        self.interval    = task.interval


        self.progress_msg_id = 0             # id сообщения с прогрессом загрузки
        self._playlist       = task.pl_type  # Если True, то запрос является плейлистом

        if self._playlist:
            self.pl_element = task.pl_element # Порядковый номер элемента в плейлисте
            self.pl_size    = task.pl_size    # Размер плейлиста

        self.vk_user_auth = task.vk_user_auth # Приготовленное api пользователя для загрузки сразу же в его аккаунт

        self.path    = ""                     # Путь сохранения файла
        # Запись основных полей в таблицу `convert_requests`
        self.task_id = vars.db.init_convert_request(self.msg_reply, self.url)

        logger.debug(f'Получена задача ({self.task_id}): {task}')

    def _getAudioBitrate(self, attempts = 0) -> int:
        """Извлечение битрейта аудио.

        Args:
            cmd (str): Команда для извлечения информации об аудио.
            attempts (int, optional): Количество попыток неуспешного выполнения команды. Defaults to 0.

        Raises:
            CustomError: Вызов ошибки с настраиваемым содержанием.

        Returns:
            tuple: (продолжительность аудио в сек., битрейт аудио в кб/c)
        """
        # Выход из рекурсии, если пользователь отменил выполнение запроса
        if self._stop:
            raise CustomError(ErrorType.audioProc.STOP_THREAD)
        # Выход из рекурсии, если превышено число попыток выполнения команды
        if attempts == bot_cfg.settings.max_attempts:
            logger.warning("Can't get real audio bitrate, return default volume.")
            return 128
        # Проверка на существование прямой ссылки
        proc = subprocess.Popen(cmdAudioBitrate(self.url), stderr = subprocess.PIPE, text = True, shell = True)
        audioInfo = proc.communicate()[1].strip()
        # Данная ошибка может произойти неожиданно, поэтому приходится повторять попытку выполнения команды через определённое время
        pos_bitrate = audioInfo.find("bitrate:")
        if audioInfo.find("bitrate:") == -1:
            attempts += 1
            logger.error(f"Ошибка получения информации об аудио ({attempts}):\n{audioInfo}")
            time.sleep(bot_cfg.settings.time_attempt)
            return self._getAudioBitrate(attempts)

        bitrate = audioInfo[pos_bitrate:].split(' ')[1].strip()
        # Проверка наличия результатов работы команды
        if not bitrate:
            attempts += 1
            logger.error(f"Отсутствует битрейт ({attempts})")
            time.sleep(bot_cfg.settings.time_attempt)
            return self._getAudioBitrate(attempts)
        logger.debug(f"Битрейт получен ({attempts}): {bitrate}")
        # Выход из рекурсии, если информация была успешно получена
        return int(bitrate)

    def _downloadAudio(self, cmd: str):
        """Загрузка видео и его конвертация в mp3 файл.

        Args:
            cmd (str): Cmd команда для загрузки и конвертации видео.

        Raises:
            CustomError: Пользовательская ошибка.
        """
        if self._stop:
            raise CustomError(ErrorType.audioProc.STOP_THREAD)
        logger.debug(f'Скачивание видео началось')
        pl_suffix = f" [{self.pl_element}/{self.pl_size}]" if self._playlist else ""

        self.progress_msg_id = sayOrReply(self.user_id, 'Загрузка началась' + pl_suffix, self.msg_reply)
        last_msg_time = time.time()
        proc = subprocess.Popen(cmd, stdout = subprocess.PIPE, stderr = subprocess.PIPE, text = True, shell = True)
        line = str(proc.stderr.readline())
        while line:
            if self._stop:
                raise CustomError(ErrorType.audioProc.STOP_THREAD)
            if "size=" in line.lower():
                # Обновление сообщения с процессом загрузки по интервалы (необходимо для предотвращения непреднамеренного спама)
                if round(time.time() - last_msg_time) >= bot_cfg.settings.msg_period:
                    size = line[6:].strip()
                    size = int(size[:size.find(' ')-2])
                    if size:
                        vars.api.bot.messages.edit(peer_id = self.user_id, message = f"Загружено {int(round(size * 1024 / self.file_size, 2) * 100)}% ({round(size / 1024, 2)} / {round(self.file_size / 1024**2, 2)} Мб)" + pl_suffix, message_id = self.progress_msg_id)
                    last_msg_time = time.time()
            line = str(proc.stderr.readline())

        stdout, stderr = proc.communicate()
        logger.debug(f"LOG:\n\tSTDOUT:\n{stdout.strip()}\n\tSTDERR:\n{stderr.strip()}")
        # Обработка возникшей в процессе загрузки ошибки
        if stdout: yt_dlpShell.define_error_type(stdout)

        # msg = "Загрузка песни завершена. Началась обработка" + pl_suffix
        # vars.api.bot.messages.edit(peer_id = self.user_id, message = msg, message_id = self.progress_msg_id)
        logger.debug(f'Скачивание видео завершено')

    def _analyzeTitle(self, video_title: str, channel: str) -> tuple:
        """Извлечение из полного заголовка видео название работы.

        Args:
            video_title (str): Полный заголовок видео.

        Returns:
            str: Название самой работы (песни) без хештегов и авторов.
        """

        logger.debug(f"Original data: \n\tTitle: {video_title}\n\tAuthor: {channel}")
        title, author = video_title, channel
        try:
            for symbol in ['-', '–', '—', '|']:
                if symbol in video_title:
                    sliced_title = list(map(str.strip, filter(None, video_title.split(symbol))))
                    title = sliced_title[-1]
                    if not author:
                        author = sliced_title[0]
                    break
            for symbol in ['\"', '\'']:
                if title.count(symbol) > 1:
                    right_quote = title.rfind(symbol)
                    title = title[title.rfind("\"", 0, right_quote)+1:right_quote]
                    break
        except Exception as er:
            logger.error(f"Can't analyze video tittle: {er}")
        if not author:
            author = "Unknown"
        return title, author

    def _vk_send_audio(self, audio_id: int, audio_owner: int):
        """Функция ддля отправки сообщенния с прикреплённой аудиозаписью

        Args:
            audio_id (int): Id ранее загруженной песни в вк.
            audio_owner (int): Id владельца этой песни.
        """
        attachment = f'audio{audio_owner}_{audio_id}'
        if self._playlist:
            vars.api.bot.messages.send(peer_id = self.user_id, attachment = attachment, random_id = get_random_id())
            # Обновление статуса компонента плейлиста в отчёте
            vars.playlist.playlist_result[self.user_id][self.pl_element][0] = bot_cfg.playlistStates.PLAYLIST_SUCCESSFUL
        else:
            vars.api.bot.messages.send(peer_id = self.user_id, attachment = attachment, reply_to = self.msg_reply, random_id = get_random_id())

    def _save_audio(self, audio_obj: dict, api_agent: vk_api.vk_api.VkApiMethod, new_owner: int):
        new_audio_id = 0
        try:
            new_audio_id = api_agent.audio.add(audio_id=audio_obj.get(VkAudio.AUDIO_ID), owner_id=audio_obj.get(VkAudio.OWNER_ID))
        except vk_api.exceptions.ApiError as er:
            if er.code == 15:
                logger.warning(f"User has closed his audio libriary. Run new uploading...\nDescription: {er}")
            else: logger.error(f"Unexpected error during saving audio ({er.code}):\nDescription: {er}")
        else:
            # Словарь для последущей записи песни в таблицу `vk_aduio`
            audio_obj[VkAudio.AUDIO_ID] = new_audio_id
            audio_obj[VkAudio.OWNER_ID] = new_owner
            vars.db.insert_audio(audio_obj)
        return new_audio_id

    def _check_existence(self, is_agent: bool) -> int:
        """Проверка существования запроса с таким же url.

        Returns:
            int: Id ранее загруженной аудизаписи.
        """
        # Отменяем проверку, если текущий запрос содержит новые тайминги для песни
        if self.interval: return None
        audio_obj = vars.db.select_original_audio(self.url, self.user_id)
        if not audio_obj: return None
        # Редактируем название песни
        audio_id       = audio_obj.get(VkAudio.AUDIO_ID)
        owner_id       = audio_obj.get(VkAudio.OWNER_ID)
        api_agent = vars.api.agent
        if is_agent:
            api_agent = self.vk_user_auth.get_api()
            if owner_id != self.user_id:
                audio_id = self._save_audio(audio_obj, api_agent, self.user_id)
                owner_id = self.user_id
        elif owner_id != bot_cfg.auth.agent_id:
            audio_id = self._save_audio(audio_obj, api_agent, bot_cfg.auth.agent_id)
            owner_id = bot_cfg.auth.agent_id

        if audio_id:
            if self.song_name and self.song_author:
                api_agent.audio.edit(audio_id=audio_id, owner_id=owner_id, title=self.song_name, artist=self.song_author)
            elif self.song_name:
                api_agent.audio.edit(audio_id=audio_id, owner_id=owner_id, title=self.song_name)
            # Отправляем ответное сообщение с песней
            self._vk_send_audio(audio_id, owner_id)
        return audio_id

    def run(self):
        """Запуск воркера в отдельном потоке.

        Raises:
            CustomError: Вызов ошибки с настраиваемым содержанием.
        """
        logger.info('AudioWorker: Запуск.')
        task_values = dict()
        task_start_time = time.time()
        user_settiings : dict = vars.db.select_user_settings(self.user_id)
        try:
            audio_id = self._check_existence(user_settiings.get(UserSettings.IS_AGENT))
            # Завершаем задачу, если песня содержится в таблице `vk_audio`
            if audio_id:
                task_values['audio_id'] = audio_id
                return

            download_string = " ".join([
                'yt-dlp',
                '--no-playlist',
                '--no-warnings',
                '--retries {attempts}',
                '--retry-sleep {sleep}',
                '--no-part',
                '-f "bestaudio/best"',
                '--audio-format "mp3"',
                '-x',
                '-o "{path}.%(ext)s"',
                '--downloader "ffmpeg"',
                '--downloader-args',
                '"ffmpeg:-hide_banner',
                '-loglevel error',
                '-stats"',
                '{interval}',
                '{url!r}'])
            title           = ""
            author          = ""

            # Получение необходимой информации об аудио
            audioInfo = yt_dlp.YoutubeDL(ydl_opts).extract_info(self.url, download=False)
            if not audioInfo:
                raise CustomError(ErrorType.audioProc.NO_INFO)

            audio_duration = int(audioInfo.get("duration", 0))
            self.path = audioInfo.get("id", None)
            if not (audio_duration and self.path):
                raise CustomError(ErrorType.audioProc.NO_INFO)
            title, author = self._analyzeTitle(audioInfo.get("title"), audioInfo.get("channel"))
            logger.debug(f"Информация об аудио успешно получена: {audio_duration}, {title}, {author}")

            # Обработка времени среза в случае, если оно указано
            audioSection = ""
            if self.interval:
                audio_interval = self.interval
                is_interval = (audio_interval.replace('-', '').replace(':', '').replace(' ', '').isnumeric() and audio_interval.count('-') == 1)
                if is_interval:
                    audio_interval = audio_interval.replace(' ', '')
                    timestamps = []
                    for timestamp in audio_interval.split('-'):
                        if not timestamp:
                            continue
                        if timestamp.count(':') > 3:
                            raise CustomError(ErrorType.audioProc.BAD_TIME_FORMAT)
                        in_seconds = 0
                        for i, tmt in enumerate(reversed(list(map(int, timestamp.split(':'))))):
                            in_seconds += tmt * 60**i
                        if in_seconds > audio_duration:
                            raise CustomError(ErrorType.audioProc.INCORRECT_TIME)
                        timestamps.append(in_seconds)
                    interval_duration = audio_duration
                    if len(timestamps) == 1:
                        if audio_interval.startswith('-'): interval_duration = timestamps[0]
                        else: interval_duration -= timestamps[0]
                    else: interval_duration = timestamps[1] - timestamps[0]
                    if interval_duration <= 0 or interval_duration > audio_duration:
                        raise CustomError(ErrorType.audioProc.INCORRECT_DURATION)
                    audio_duration = interval_duration
                    audio_interval = '*' + audio_interval
                audioSection = f'--force-keyframes-at-cuts --download-sections "{audio_interval}"'
            logger.debug(f"Актуальная длительность видео: {audio_duration}")

            # Приблизительный вес файла
            self.file_size = audio_duration * self._getAudioBitrate() * 128 #  F (bytes) = t (s) * bitrate (kb / s) * 1024 // 8

            # Проверка размера файла (необходимо из-за внутренних ограничений VK)
            logger.debug(f"Предварительный размер файла: {round(self.file_size / 1024**2, 2)} Mb")
            if self.file_size * 0.85 > bot_cfg.settings.max_filesize:
                raise CustomError(ErrorType.audioProc.HIGH_PREV_SIZE)

            self.path = str(self.user_id) + self.path
            download_string = download_string.format(
                path=self.path,
                url=self.url,
                interval=audioSection,
                attempts=bot_cfg.settings.max_attempts,
                sleep=bot_cfg.settings.time_attempt
            )
            self.path += ".mp3"

            # Скачивание аудио
            self._downloadAudio(download_string)
            # Получение реального размера файла
            self.file_size = os.path.getsize(self.path)
            # Проверка размера файла (необходимо из-за внутренних ограничений VK)
            logger.debug(f"Фактический размер файла: {round(self.file_size / 1024**2, 2)} Mb")
            if self.file_size > bot_cfg.settings.max_filesize:
                raise CustomError(ErrorType.audioProc.HIGH_REAL_SIZE)
            else:
                if self.song_name:   title  = self.song_name
                if self.song_author: author = self.song_author
                if len(title) > 50:  title  = title[0:51]
                if len(author) > 50: author = author[0:51]
                # Остановка загрузки аудио в Вк, если пользователь отменил выполнение запроса
                if self._stop:
                    raise CustomError(ErrorType.audioProc.STOP_THREAD)
                # Загрузка аудиозаписи на сервера VK + её отправка получателю
                agent_upload = vars.api.agent_upload
                if self.vk_user_auth:
                    if user_settiings.get(UserSettings.IS_AGENT):
                        agent_upload = vk_api.VkUpload(self.vk_user_auth)
                audio_obj : dict = agent_upload.audio(self.path, author, title)
                audio_id       = audio_obj.get('id')
                audio_owner_id = audio_obj.get('owner_id')

                # Словарь для последущей записи песни в таблицу `vk_aduio`
                audio_values = dict()
                audio_values[VkAudio.AUDIO_ID]       = audio_id
                audio_values[VkAudio.OWNER_ID]       = audio_owner_id
                audio_values[VkAudio.AUDIO_DURATION] = audio_obj.get('duration')
                audio_values[VkAudio.IS_SEGMENTED]   = bool(self.interval)

                if vars.db.insert_audio(audio_values):
                    task_values['audio_id'] = audio_id

                self._vk_send_audio(audio_id, audio_owner_id)

        except CustomError as er:
            # Обработка ошибок, не относящихся к преднамеренной остановке потока
            task_values['error_description'] = er.code
            if (er.code != ErrorType.audioProc.STOP_THREAD.value) and (not self._playlist):
                sayOrReply(self.user_id, er.description, self.msg_reply)
            logger.error(f'Custom: {er}')

        except vk_api.exceptions.ApiError as er:
            task_values['error_description'] = er.code
            if self._playlist:
                # Ошибка авторских прав
                if er.code == 270 and self.pl_element:
                    vars.playlist.playlist_result[self.user_id][self.pl_element][0] = bot_cfg.playlistStates.PLAYLIST_COPYRIGHT
            else:
                err_msg_default = "Невозможно обработать запрос. Убедитесь, что запрос корректный, и отправьте его повторно"
                err_str = f'Ошибка: {vkapi_errors.get(er.code, err_msg_default)}.'
                sayOrReply(self.user_id, err_str, self.msg_reply)
            # Добавить проверку через sql на успешность загрузки видео — UPD: забыл зачем
            logger.error(f'VK API: \n\tCode: {er.code}\n\tBody: {er}')

        except Exception as er:
            task_values['error_description'] = str(er)
            # Обработка ошибок, не относящихся к компонентам плейлиста
            if not self._playlist:
                err_str = 'Ошибка: Невозможно обработать запрос. Убедитесь, что запрос корректный, и отправьте его повторно.'
                sayOrReply(self.user_id, err_str, self.msg_reply)
            logger.error(f'Исключение: {er}')

        finally:
            # Удаление загруженного файла
            if os.path.isfile(self.path):
                os.remove(self.path)
                logger.debug(f'Успешно удалил аудио-файл: {self.path}')
            else:
                logger.warning('Аудиофайл не существует')

            # Удаление сообщения с прогрессом
            deleteMsg(self.progress_msg_id)
            # Запись оставшихся полей в таблицу `convert_requests`
            task_values['process_time'] = round(time.time() - task_start_time, 2)
            if self.task_id: vars.db.complete_convert_request(self.task_id, task_values)
            else: logger.error("task_id is null, can't complete convert request")
            # Подтверждение запроса и переход с следующему, если задача ранее не была остановлена
            if not self._stop: vars.queue.ack_request(self.user_id, threading.current_thread())

    def stop(self):
        """Вынужденная остановка воркера.
        """
        self._stop = True
