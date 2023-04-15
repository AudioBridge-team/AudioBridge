#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import os
import threading, subprocess
import time

import yt_dlp

import vk_api
from vk_api.utils import get_random_id

from audiobridge.utils.customErrors import CustomError, vkapi_errors

from audiobridge.utils.sayOrReply import sayOrReply
from audiobridge.utils.deleteMsg import deleteMsg
from audiobridge.utils.yt_dlpShell import Yt_dlpShell

from audiobridge.config.bot import cfg as bot_cfg
from audiobridge.config.handler import vars, WorkerTask


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
        self._stop     = False
        self._task     = task

    def _getAudioBitrate(self, url: str, attempts = 0) -> int:
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
            raise CustomError(code=bot_cfg.customoErrCode.STOP_THREAD)
        # Выход из рекурсии, если превышено число попыток выполнения команды
        if attempts == bot_cfg.settings.max_attempts:
            logger.warning("Can't get real audio bitrate, return default volume.")
            return 128
        # Проверка на существование прямой ссылки
        proc = subprocess.Popen(cmdAudioBitrate(url), stderr = subprocess.PIPE, text = True, shell = True)
        audioInfo = proc.communicate()[1].strip()
        # Данная ошибка может произойти неожиданно, поэтому приходится повторять попытку выполнения команды через определённое время
        pos_bitrate = audioInfo.find("bitrate:")
        if audioInfo.find("bitrate:") == -1:
            attempts += 1
            logger.error(f"Ошибка получения информации об аудио ({attempts}):\n{audioInfo}")
            time.sleep(bot_cfg.settings.time_attempt)
            return self._getAudioBitrate(url, attempts)

        bitrate = audioInfo[pos_bitrate:].split(' ')[1].strip()
        # Проверка наличия результатов работы команды
        if not bitrate:
            attempts += 1
            logger.error(f"Отсутствует битрейт ({attempts})")
            time.sleep(bot_cfg.settings.time_attempt)
            return self._getAudioBitrate(url, attempts)
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
        logger.debug(f'Скачивание видео началось')
        pl_suffix = f" [{self.task_id}/{self.task_size}]" if self._playlist else ""

        self.progress_msg_id = sayOrReply(self.user_id, 'Загрузка началась' + pl_suffix, self.msg_reply)
        last_msg_time = time.time()
        proc = subprocess.Popen(cmd, stdout = subprocess.PIPE, stderr = subprocess.PIPE, text = True, shell = True)
        line = str(proc.stderr.readline())
        while line:
            if self._stop:
                raise CustomError(code=bot_cfg.customoErrCode.STOP_THREAD)
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

        msg = "Загрузка файла завершена. Началась обработка" + pl_suffix
        vars.api.bot.messages.edit(peer_id = self.user_id, message = msg, message_id = self.progress_msg_id)
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

    def run(self):
        """Запуск воркера в отдельном потоке.

        Raises:
            CustomError: Вызов ошибки с настраиваемым содержанием.
        """
        logger.info('AudioWorker: Запуск.')
        try:
            # id сообщения с размером очереди (необходимо для удаления в конце обработки запроса)
            self.msg_start       = self._task.msg_start
            # id пользователя
            self.user_id         = self._task.user_id
            # id сообщения пользователя (необходимо для ответа на него)
            self.msg_reply       = self._task.msg_reply

            # id сообщения с прогрессом загрузки
            self.progress_msg_id = 0
            # Если True, то запрос является плейлистом
            self._playlist       = self._task.pl_type

            if self._playlist:
                # Порядковый номер элемента в плейлисте
                self.task_id   = self._task.pl_element
                # Размер плейлиста
                self.task_size = self._task.pl_size
            # Путь сохранения файла

            self.path            = ""

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

            logger.debug(f'Получена задача: {self._task}')

            audio_duration = 0
            author = ""
            # Получение необходимой информации об аудио
            audioInfo = yt_dlp.YoutubeDL(ydl_opts).extract_info(self._task.url, download=False)
            if not audioInfo:
                raise CustomError("Ошибка: Невозможно получить информацию о видео.")

            audio_duration = int(audioInfo.get("duration", 0))
            self.path = audioInfo.get("id", None)
            if not (audio_duration and self.path):
                raise CustomError("Ошибка: Невозможно получить информацию о видео.")
            self.title, author = self._analyzeTitle(audioInfo.get("title"), audioInfo.get("channel"))
            logger.debug(f"Информация об аудио успешно получена: {audio_duration}, {self.title}, {author}")

            # Обработка времени среза в случае, если оно указано
            audioSection = ""
            if self._task.interval:
                audio_interval = self._task.interval
                is_interval = (audio_interval.replace('-', '', 1).replace(':', '').replace(' ', '').isnumeric() and audio_interval.count('-') == 1)
                if is_interval:
                    audio_interval = audio_interval.replace(' ', '')
                    timestamps = []
                    for timestamp in audio_interval.split('-'):
                        if not timestamp:
                            continue
                        if timestamp.count(':') > 3:
                            raise CustomError('Ошибка: Неверный формат времени среза.')
                        in_seconds = 0
                        for i, tmt in enumerate(reversed(list(map(int, timestamp.split(':'))))):
                            in_seconds += tmt * 60**i
                        if in_seconds > audio_duration:
                            raise CustomError('Ошибка: Некорректное время среза.')
                        timestamps.append(in_seconds)
                    interval_duration = audio_duration
                    if len(timestamps) == 1:
                        if audio_interval.startswith('-'): interval_duration = timestamps[0]
                        else: interval_duration -= timestamps[0]
                    else: interval_duration = timestamps[1] - timestamps[0]
                    if interval_duration <= 0 or interval_duration > audio_duration:
                        raise CustomError('Ошибка: Некорректная продолжительность среза.')
                    audio_duration = interval_duration
                    audio_interval = '*' + audio_interval
                audioSection = f'--force-keyframes-at-cuts --download-sections "{audio_interval}"'
            logger.debug(f"Актуальная длительность видео: {audio_duration}")

            # Приблизительный вес файла
            self.file_size = audio_duration * self._getAudioBitrate(self._task.url) * 128 #  F (bytes) = t (s) * bitrate (kb / s) * 1024 // 8

            # Проверка размера файла (необходимо из-за внутренних ограничений VK)
            logger.debug(f"Предварительный размер файла: {round(self.file_size / 1024**2, 2)} Mb")
            if self.file_size * 0.85 > bot_cfg.settings.max_filesize:
                raise CustomError('Ошибка: Размер аудиозаписи превышает 200 Мб!')

            self.path = str(self.user_id) + self.path
            download_string = download_string.format(
                path=self.path,
                url=self._task.url,
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
                raise CustomError('Размер аудиозаписи превышает 200 Мб!')
            else:
                if self._task.song_name:
                    self.title = self._task.song_name
                if self._task.song_author:
                    author = self._task.song_author
                if len(self.title) > 50:
                    self.title = self.title[0:51]
                # Остановка загрузки аудио в Вк, если пользователь отменил выполнение запроса
                if self._stop:
                    raise CustomError(code=bot_cfg.customoErrCode.STOP_THREAD)
                # Загрузка аудиозаписи на сервера VK + её отправка получателю
                audio_obj = vars.api.agent_upload.audio(self.path, author, self.title)
                audio_id = audio_obj.get('id')
                audio_owner_id = audio_obj.get('owner_id')
                attachment = f'audio{audio_owner_id}_{audio_id}'

                if self._playlist:
                    vars.api.bot.messages.send(peer_id = self.user_id, attachment = attachment, random_id = get_random_id())
                    # Обновление статуса компонента плейлиста в отчёте
                    vars.playlist.playlist_result[self.user_id][self.task_id][0] = bot_cfg.playlistStates.PLAYLIST_SUCCESSFUL
                else:
                    vars.api.bot.messages.send(peer_id = self.user_id, attachment = attachment, reply_to = self.msg_reply, random_id = get_random_id())

        except CustomError as er:
            # Обработка ошибок, не относящихся к преднамеренной остановке потока
            if er.code != bot_cfg.customoErrCode.STOP_THREAD:
                if not self._playlist:
                    sayOrReply(self.user_id, er, self.msg_reply)
                logger.error(f'Custom: {er}')

        except vk_api.exceptions.ApiError as er:
            if self._playlist:
                # Ошибка авторских прав
                if er.code == 270 and self.task_id:
                    vars.playlist.playlist_result[self.user_id][self.task_id][0] = bot_cfg.playlistStates.PLAYLIST_COPYRIGHT
            else:
                error_string = 'Ошибка: {error_msg}.'
                error_msg_default = "Невозможно обработать запрос. Убедитесь, что запрос корректный, и отправьте его повторно"
                if er.code == 15 and self.file_size < 50 * 1024 :
                    error_string = error_string.format(error_msg = vkapi_errors.get(er.code))
                elif er.code == 100 and "server is undefined" in er.error['error_msg'].lower():
                    error_string = error_string.format(error_msg = vkapi_errors.get(er.code))
                else:
                    error_string = error_string.format(error_msg = vkapi_errors.get(er.code, error_msg_default))

                sayOrReply(self.user_id, f'{error_string}', self.msg_reply)
            # Добавить проверку через sql на успешность загрузки видео
            logger.error(f'VK API: \n\tCode: {er.code}\n\tBody: {er}')

        except Exception as er:
            # Обработка ошибок, не относящихся к компонентам плейлиста
            if not self._playlist:
                error_string = 'Ошибка: Невозможно обработать запрос. Убедитесь, что запрос корректный, и отправьте его повторно.'
                sayOrReply(self.user_id, error_string, self.msg_reply)
            logger.error(f'Исключение: {er}')

        finally:
            # Удаление загруженного файла
            if os.path.isfile(self.path):
                os.remove(self.path)
                logger.debug(f'Успешно удалил аудио-файл: {self.path}')
            else:
                logger.error('Ошибка: Аудио-файл не существует.')

            # Удаление сообщения с прогрессом
            deleteMsg(self.progress_msg_id)

            if not self._stop:
                logger.debug('Reached a stop-condition')
                # Удаление сообщения с порядком очереди
                if vars.userRequests[self.user_id] < 0:
                    vars.userRequests[self.user_id] += 1
                    if vars.userRequests[self.user_id] == -1:
                        vars.userRequests[self.user_id] = 0
                        deleteMsg(self.msg_start)
                        vars.playlist.summarize(self.user_id)
                else:
                    vars.userRequests[self.user_id] -= 1
                    deleteMsg(self.msg_start)
                logger.debug('Reached receiving a report')
                # Отчёт о проделанной работе
                logger.debug(
                    (
                        'Завершено:\n'+
                        '\tЗадача: {0}\n' +
                        '\tПуть: {1}\n' +
                        '\tОчередь текущего пользователя ({2}): {3}\n' +
                        '\tОчередь текущего worker\'а: {4}'
                    ).format(
                        self._task,
                        self.path,
                        self.user_id,
                        vars.userRequests[self.user_id],
                        vars.queue.size_queue
                    )
                )
                # Очистка памяти, в случае пустой переменной
                if not vars.userRequests[self.user_id]:
                    del vars.userRequests[self.user_id]
                # Подтверждение выполненной задачи потоком
                vars.queue.ack_request(self.user_id, threading.current_thread())
            else:
                # Отчёт о проделанной обратки
                logger.debug(
                    (
                        'Завершено:\n'+
                        '\tЗадача: {0}\n' +
                        '\tПуть: {1}\n' +
                        '\tОчередь текущего пользователя ({2}): null\n' +
                        '\tОчередь текущего worker\'а: null'
                    ).format(
                        self._task,
                        self.path,
                        self.user_id
                    )
                )

    def stop(self):
        """Вынужденная остановка воркера.
        """
        self._stop = True
