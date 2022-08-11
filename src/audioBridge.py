import logging
import time
from sys import platform
from logging import StreamHandler, Formatter
from queue import Queue
from datetime import datetime
import os
import sys
import locale
import threading
import subprocess
import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.utils import get_random_id

vk_session_music = vk_api.VkApi(token='')
upload = vk_api.VkUpload(vk_session_music)
vk_user = vk_session_music.get_api()

vk_session = vk_api.VkApi(token='')
vk = vk_session.get_api()

logger = logging.getLogger("logger")
logger.setLevel(logging.DEBUG)
handler = StreamHandler(stream=sys.stdout)
handler.setFormatter(Formatter(fmt='[%(asctime)s, %(levelname)s] ~ %(threadName)s (%(funcName)s)\t~: %(message)s', datefmt=time.strftime('%d-%m-%y %H:%M:%S')))
logger.addHandler(handler)

userReqCount = []                           #для отслеживания кол-ва запросов от одного пользователя MAX_REQUESTS_QUEUE

MAX_FILESIZE = 200 * 1024 * 1024            #максимальный размер аудиофайла
MSG_PERIOD = 50                             #период обновления процесса загрузки файла на сервер
MAX_REQUESTS_QUEUE = 5                      #максимальное кол-во запросов в общую очередь от одного пользователя
MAX_WORKERS = 6                             #число потоков обработки запросов
MAX_VIDEO_DURATION = 3 * 60 * 60            #максимальная длительность видео в секундах
MAX_ATTEMPTS = 3                            #количество попыток при ошибке скачивания
TIME_ATTEMPT = 1                            #интервал между попытками скачивания (сек)

class MyVkBotLongPoll(VkBotLongPoll):
    def listen(self):
        while True:
            try:
                for event in self.check():
                    yield event
            except Exception as e:
                logger.error(e)

class CustomError(Exception):
    def __init__(self, text):
        self.txt = text

#работа со строкой времени
def getSeconds(strTime):
    strTime = strTime.strip()
    try:
        pattern = ''
        if strTime.count(":") == 1:
            pattern = '%M:%S'
        if strTime.count(":") == 2:
            pattern = '%H:%M:%S'
        if pattern:
            time_obj = datetime.strptime(strTime, pattern)
            return time_obj.hour * 60 * 60 + time_obj.minute * 60 + time_obj.second
        else:
            return int(float(strTime))
    except Exception as er:
        logger.error(er)
        return -1

#получить информацию о видео по ключу
def getVideoInfo(key, url):
    return 'youtube-dl --max-downloads 1 --no-warnings --get-filename -o "%({0})s" {1}'.format(key, url)

class AudioWorker:
    def __init__(self, queue: Queue):
        self._queue = queue

    def start_handling(self):
        logger.info(f'Started')
        while True:
            try:
                options = self._queue.get()

                param = options.pop(0)
                self.msg_start_id = param[0]    #id сообщения с размером очереди
                self.user_id = param[1]         #id пользователя
                self.msg_id = param[2]          #id сообщения (необходимо для его редактирования)
                self.path = ""                  #путь сохранения фалйа
                self.progress_msg_id = 0        #id сообщения с прогрессом загрузки

                if options[0][0] == '-':
                    logger.warning("Attempt to crash!")
                    raise CustomError("Невалидный URL youtube видео!")

                downloadString = 'youtube-dl --no-warnings --newline --id --extract-audio --audio-format mp3 --max-downloads 1 "{0}"'.format(options[0])
                cUpdateProcess = -1

                logger.debug(f'Got task: {options}')

                attempts = 0
                video_duration = -1
                while attempts != MAX_ATTEMPTS:
                    #проверка на соблюдение ограничения длительности видео (MAX_VIDEO_DURATION)
                    proc = subprocess.Popen(getVideoInfo('duration', options[0]), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True)
                    stdout, stderr = proc.communicate()
                    if(stderr):
                        logger.error(f"Getting video duration ({attempts}): {stderr.strip()}")
                        if('HTTP Error 403' in stderr):
                            attempts += 1
                            time.sleep(TIME_ATTEMPT)
                            continue
                        elif('Sign in to confirm your age' in stderr):
                            raise CustomError("Невозможно скачать видео из-за возрастных ограничений!")
                        elif('Video unavailable' in stderr):
                            raise CustomError("Видео недоступно из-за авторских прав или других причин!")
                        else:
                            raise CustomError("Невалидный URL youtube видео!")
                    video_duration = getSeconds(stdout)
                    if video_duration != -1:
                        break
                logger.debug(f'Getting video duration (in seconds) attempts: {attempts}')

                if video_duration == -1:
                    raise CustomError("Возникла неизвестная ошибка, обратитесь к разработчику...")
                elif video_duration > MAX_VIDEO_DURATION:
                    raise CustomError("Длительность будущей аудиозаписи превышает 3 часа!")

                #обработка запроса с таймингами среза
                if len(options) > 3:
                    startTime = getSeconds(options[3])
                    if startTime == -1:
                        raise CustomError("Неверный формат времени среза!")
                    audioDuration = video_duration - startTime
                    if len(options) == 5:
                        audioDuration = getSeconds(options[4]) - startTime

                #загрузка файла
                attempts = 0
                while attempts != MAX_ATTEMPTS:
                    proc = subprocess.Popen(downloadString, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True)
                    line = str(proc.stdout.readline())
                    while line:
                        #поиск пути сохранения файла
                        if 'Destination' in line and '.mp3' in line:
                            self.path = line[line.find(':')+2:len(line)].strip()
                            logger.debug(f"Path: {self.path}")
                        #обновление сообщения с процессом загрузки файла
                        if ' of ' in line:
                            if cUpdateProcess == -1:
                                self.progress_msg_id=vk.messages.send(peer_id=self.user_id, message="Загрузка началась...", reply_to=self.msg_id, random_id=get_random_id())
                            if cUpdateProcess == MSG_PERIOD:
                                progress = line[line.find(' '):line.find('KiB/s')+5].strip()
                                if progress:
                                    vk.messages.edit(peer_id=self.user_id, message=progress, message_id=self.progress_msg_id)
                                cUpdateProcess = 0
                            if ' in ' in line:
                                progress = line[line.find(' '):len(line)].strip()
                                if progress: vk.messages.edit(peer_id=self.user_id, message=progress, message_id=self.progress_msg_id)
                            cUpdateProcess += 1
                        line = str(proc.stdout.readline())
                    stdout, stderr = proc.communicate()
                    if(stderr):
                        if('HTTP Error 403' in stderr): #ERROR: unable to download video data: HTTP Error 403: Forbidden
                            attempts += 1
                            time.sleep(TIME_ATTEMPT)
                            continue
                        else:
                            logger.error(f"Downloading video ({attempts}): {stderr.strip()}")
                            raise CustomError("Невозможно скачать видео!")
                    else:
                        break
                logger.debug(f"Downloading video attempts: {attempts}")

                #проверка валидности пути сохранения фалйа
                if not self.path:
                    logger.error(f"Path: attempts - {attempts}")
                    raise CustomError("Невалидный URL youtube видео!")
                #проверка размера фалйа (необходимо из-за внутренних ограничений VK)
                if os.path.getsize(self.path) > MAX_FILESIZE:
                    raise CustomError("Размер аудиозаписи превышает 200 Мб!")
                else:
                    os.rename(self.path, 'B' + self.path)
                    self.path = 'B' + self.path
                    #создание аудиосегмента
                    if len(options) > 3 and audioDuration < video_duration:
                        baseAudio = self.path
                        self.path = 'A' + self.path
                        audioString = "ffmpeg -ss {0} -t {1} -i {2} {3}".format(startTime, audioDuration, baseAudio, self.path)
                        logger.debug(f"Audio string: {audioString}")
                        subprocess.Popen(audioString, stdout=subprocess.PIPE, text=True, shell=True).wait()
                        if os.path.isfile(baseAudio):
                            os.remove(baseAudio)
                            logger.debug(f"Delete video file successful: {baseAudio}")
                        else:
                            logger.error(f"Video file doesn't exist")

                    #поиск и коррекция данных аудиозаписи
                    artist = "unknown"
                    title = "unknown"
                    #URL
                    if len(options) == 1:
                        proc = subprocess.Popen(getVideoInfo('title', options[0]), stdout=subprocess.PIPE, text=True, shell=True)
                        file_name = proc.communicate()[0].strip()
                        if file_name:
                            title = file_name
                        proc = subprocess.Popen(getVideoInfo('channel', options[0]), stdout=subprocess.PIPE, text=True, shell=True)
                        file_author = proc.communicate()[0].strip()
                        if file_author:
                            artist = file_author
                    #URL + song_name
                    elif len(options) == 2:
                        title = options[1]
                        proc = subprocess.Popen(getVideoInfo('channel', options[0]), stdout=subprocess.PIPE, text=True, shell=True)
                        file_author = proc.communicate()[0].strip()
                        if file_author:
                            artist = file_author
                    #URL + song_name + song_autor
                    else:
                        artist = options[2]
                        title = options[1]
                    if len(title) > 50:
                        title[0:51]

                    #загрузка аудиозаписи на сервера VK + её отправка получателю
                    audio_obj = upload.audio(self.path, artist, title)
                    audio_id = audio_obj.get('id')
                    audio_owner_id = audio_obj.get('owner_id')
                    attachment = f"audio{audio_owner_id}_{audio_id}"
                    vk.messages.send(peer_id=self.user_id, attachment=attachment, reply_to=self.msg_id, random_id=get_random_id())

            except CustomError as er:
                vk.messages.send(peer_id=self.user_id, message=er, reply_to=self.msg_id, random_id=get_random_id())
                logger.error(f"Custom: {er}")

            except Exception as er:
                error_string = "Невозможно загрузить, проверьте корректность своего запроса и отправьте его повторно..."
                if '[270]' in str(er):
                    error_string = "Правообладатель ограничил доступ к данной аудиозаписи. Загрузка прервана"
                vk.messages.send(peer_id=self.user_id, message=error_string, reply_to=self.msg_id, random_id=get_random_id())
                logger.error(f"Exception: {er}")

            finally:
                #удаление сообщения с порядком очереди
                vk.messages.delete(delete_for_all=1, message_ids=self.msg_start_id)
                #удаление сообщения с прогрессом
                if(self.progress_msg_id):
                    vk.messages.delete(delete_for_all=1, message_ids=self.progress_msg_id)

                #удаление загруженного файла
                if os.path.isfile(self.path):
                    os.remove(self.path)
                    logger.debug(f"Delete audio file successful: {self.path}")
                else:
                    logger.error("Audio file doesn't exist")

                userReqCount.remove(self.user_id)
                logger.debug(("Finished:\n"+
                            "\tTask: {0}\n" +
                            "\tCurrent user ({1}) queue: {2}\n" +
                            "\tCurrent worker queue: {3}").format(options, self.user_id, userReqCount.count(self.user_id), self._queue.qsize()))

class VkBotWorker():
    def __init__(self):
        self.longpoll = MyVkBotLongPoll(vk_session, '212269992')
        self.queueUsers = Queue()
        threads = []
        for i in range(MAX_WORKERS):
            threads.append(threading.Thread(target=AudioWorker(self.queueUsers).start_handling))
            threads[i].name = f'{i}-th worker'
            threads[i].start()

    def listen_longpoll(self):
        for event in self.longpoll.listen():
            if event.type == VkBotEventType.MESSAGE_NEW:
                msg = event.obj.message
                user_id = msg.get('peer_id')
                message_id = msg.get('id')

                if platform == "win32":
                    if user_id != 228822387:
                        #vk.messages.send(peer_id=user_id, message="Бот обновляется, повторите, пожалуйста, свой запрос через час", reply_to=message_id, random_id=get_random_id())
                        continue

                options = list(filter(None, event.obj.message.get('text').split('\n')))
                logger.debug(f"New message: ({len(options)}) {options}")

                if userReqCount.count(user_id) == MAX_REQUESTS_QUEUE:
                    vk.messages.send(peer_id=user_id, message="Ваше количество запросов в общей очереди не может превышать {0}!".format(MAX_REQUESTS_QUEUE), random_id=get_random_id())
                else:
                    if len(options) > 5:
                        vk.messages.send(peer_id=user_id, message="Слишком много аргументов!", reply_to=message_id, random_id=get_random_id())
                        continue
                    else:
                        attachment_info = msg.get('attachments')
                        #logger.debug(attachment_info)

                        if attachment_info:
                            try:
                                logger.debug(f"Attachments info: ({len(attachment_info)}) {attachment_info[0].get('type')}")
                                attachment_type = attachment_info[0].get('type')

                                if attachment_type == "video":
                                    video_info = attachment_info[0].get('video')
                                    video_owner_id = video_info.get('owner_id')
                                    video_id = video_info.get('id')

                                    video = f'{video_owner_id}_{video_id}'
                                    logger.debug(f'Attachment video: {video}')
                                    response = vk_user.video.get(videos=video)

                                    video_url = response.get('items')[0].get('player')
                                    if len(options) > 4:
                                        options[0] = video_url
                                    else:
                                        options.insert(0, video_url)

                                elif attachment_type == "link":
                                    link_url = attachment_info[0].get('link').get('url')
                                    if options:
                                        if link_url != options[0]:
                                            options.insert(0, link_url)
                                    else:
                                        options.insert(0, link_url)

                                else:
                                    if not options:
                                        vk.messages.send(peer_id=user_id, message="Ошибка обработки запроса!", reply_to=message_id, random_id=get_random_id())
                                        continue

                            except Exception as er:
                                logger.warning(f"Attachment: {er}")
                                if not options:
                                    vk.messages.send(peer_id=user_id, message="Невозможно обработать запрос (возможно, вы прикрепили видео вместо ссылки на видео)!", reply_to=message_id, random_id=get_random_id())
                                    continue

                    userReqCount.append(user_id)
                    msg_start_id = vk.messages.send(peer_id=user_id, message="Запрос добавлен в очередь ({0}/{1})".format(userReqCount.count(user_id), MAX_REQUESTS_QUEUE), random_id=get_random_id())
                    options.insert(0, [msg_start_id, user_id, message_id])
                    self.queueUsers.put(options)

if __name__ == '__main__':
    if platform == "win32":
        logger.info("Debug mode: Windows platform")
    logger.info("Current version 1.0.1.7d")
    logger.info(f"Filesystem encoding: {sys.getfilesystemencoding()}")
    logger.info(f"Preferred encoding: {locale.getpreferredencoding()}")
    vkBotWorker = VkBotWorker()
    vkBotWorker.listen_longpoll()
