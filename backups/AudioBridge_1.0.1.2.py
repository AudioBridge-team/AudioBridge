import logging
import time
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

ACCESS_TOKEN = ''
vk_session_music = vk_api.VkApi(token=ACCESS_TOKEN)
upload = vk_api.VkUpload(vk_session_music)
vk_user = vk_session_music.get_api()

vk_session = vk_api.VkApi(token='')
vk = vk_session.get_api()

logger = logging.getLogger("logger")
logger.setLevel(logging.DEBUG)
handler = StreamHandler(stream=sys.stdout)
handler.setFormatter(Formatter(fmt='%(asctime)s: %(message)s'))
logger.addHandler(handler)

userReqCount = []                           #для отслеживания кол-ва запросов от одного пользователя MAX_REQUESTS_QUEUE

MAX_FILESIZE = 200 * 1024 * 1024            #максимальный размер аудиофайла
MSG_PERIOD = 50                             #период обновления процесса загрузки файла на сервер
MAX_REQUESTS_QUEUE = 5                      #максимальное кол-во запросов в общую очередь от одного пользователя
MAX_WORKERS = 6                             #число потоков обработки запросов
MAX_VIDEO_DURATION = 3 * 60 * 60            #максимальная длительность видео в секундах
MAX_ATTEMPTS = 3                            #количество попыток при ошибке скачивания

class MyVkBotLongPoll(VkBotLongPoll):
    def listen(self):
        while True:
            try:
                for event in self.check():
                    yield event
            except Exception as e:
                logger.debug('[VK Longpoll Error]:', e)

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
            return int(strTime)
    except Exception as er:
        logger.debug(f"[server] {er}")
        return -1

class AudioWorker:
    def __init__(self, n: int, queue: Queue):
        self.n = n
        self._queue = queue

    def start_handling(self):
        logger.debug(f'Starting {self.n}-th worker\n')
        while True:
            try:
                options = self._queue.get()
       
                self.user_id = options.pop(0)   #id пользователя
                self.msg_id = options.pop(0)    #id сообщения (необходимо для его редактирования)
                self.path = ""                  #путь сохранения фалйа

                if options[0][0] == '-':
                    logger.debug(f"Worker-{self.n} [ERROR]: attempt to crash!")
                    raise CustomError("Невалидный URL youtube видео!")

                downloadString = 'youtube-dl --newline --id --extract-audio --audio-format mp3 --max-downloads 1 "{0}"'.format(options[0])
                progress_msg_id = ""
                cUpdateProcess = -1

                logger.debug(f'Worker-{self.n} got task {options}')

                attempts = 0
                video_duration = -1
                while(attempts != MAX_ATTEMPTS):
                    #проверка на соблюдение ограничения длительности видео (MAX_VIDEO_DURATION)
                    videoString = 'youtube-dl --get-duration "{0}"'.format(options[0])
                    proc = subprocess.Popen(videoString, stdout=subprocess.PIPE, text=True, shell=True)
                    response = str(proc.stdout.readline())
                    logger.debug(f'Worker-{self.n} getting video duration [{attempts}]: {response.strip()}')
                    video_duration = getSeconds(response)
                    if video_duration == -1:
                        attempts += 1
                        time.sleep(1)
                    else: break

                if video_duration == -1:
                    raise CustomError("Невалидный URL youtube видео!")
                elif video_duration > MAX_VIDEO_DURATION:
                    raise CustomError("Длительность youtube видео превышает 3 часа!")

                #обработка запроса с таймингами среза
                if len(options) > 3: 
                    startTime = getSeconds(options[3])
                    if startTime == -1:
                        raise CustomError("Неверный формат времени среза!")
                    audioDuration = video_duration - startTime
                    if len(options) == 5:
                        audioDuration = getSeconds(options[4]) - startTime
               
                #загрузка файла
                proc = subprocess.Popen(downloadString, stdout=subprocess.PIPE, text=True, shell=True)
                line = str(proc.stdout.readline())
                while line:
                    #поиск пути сохранения файла
                    if 'Destination' in line and '.mp3' in line:
                        self.path = line[line.find(':')+2:len(line)].strip()
                        logger.debug(f"Worker-{self.n} [PATH]: {self.path}")
                    #обновление сообщения с процессом загрузки файла
                    if ' of ' in line:
                        if cUpdateProcess == -1:
                            progress_msg_id=vk.messages.send(peer_id=self.user_id, message="Загрузка началась...", reply_to=self.msg_id, random_id=get_random_id())
                        if cUpdateProcess == MSG_PERIOD:
                            progress = line[line.find(' '):line.find('KiB/s')+5].strip()
                            if progress: 
                                vk.messages.edit(peer_id=self.user_id, message=progress, message_id=progress_msg_id)
                            cUpdateProcess = 0
                        if ' in ' in line:
                            progress = line[line.find(' '):len(line)].strip()
                            if progress: vk.messages.edit(peer_id=self.user_id, message=progress, message_id=progress_msg_id)
                        cUpdateProcess += 1
                    line = str(proc.stdout.readline()) 

                #проверка валидности пути сохранения фалйа
                if not self.path:
                    raise CustomError("Невалидный URL youtube видео!")
                #проверка размера фалйа (необходимо из-за внутренних ограничений VK)
                if os.path.getsize(self.path) > MAX_FILESIZE:
                    raise CustomError("Размер аудиозаписи превышает 200 Мб!")
                else:
                    os.rename(self.path, 'B' + self.path)
                    self.path = 'B' + self.path
                    #создание аудиосегмента
                    if len(options) > 3:
                        baseAudio = self.path
                        self.path = 'A' + self.path
                        audioString = "ffmpeg -ss {0} -t {1} -i {2} {3}".format(startTime, audioDuration, baseAudio, self.path)
                        logger.debug(f"Worker-{self.n} [audio string] {audioString}")
                        subprocess.Popen(audioString, stdout=subprocess.PIPE, text=True, shell=True).wait()
                        if os.path.isfile(baseAudio): 
                            os.remove(baseAudio)
                            logger.debug(f"Worker-{self.n} [delete VIDEO file] success: {baseAudio}") 
                        else: 
                            logger.debug(f"Worker-{self.n} [ERROR]: VIDEO file doesn't exist")

                    #поиск и коррекция данных аудиозаписи
                    artist = "unknown"
                    title = "unknown"
                    #URL
                    if len(options) == 1:
                        videoString = 'youtube-dl --get-title "{0}"'.format(options[0])
                        proc = subprocess.Popen(videoString, stdout=subprocess.PIPE, text=True, shell=True)
                        file_name = str(proc.stdout.readline()).strip()
                        if file_name: 
                            title = file_name
                    #URL + song_name
                    elif len(options) == 2:
                        title = options[1]
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
                    attachment = 'audio{0}_{1}'.format(audio_owner_id, audio_id)
                    vk.messages.send(peer_id=self.user_id, attachment=attachment, reply_to=self.msg_id, random_id=get_random_id())

            except CustomError as er:
                vk.messages.send(peer_id=self.user_id, message=er, reply_to=self.msg_id, random_id=get_random_id())
                logger.debug(f"Worker-{self.n} [CUSTOM ERROR]: {er}")

            except Exception as er:
                error_string = "Невозможно загрузить, проверьте корректность своего запроса и отправьте его повторно..."
                if '[270]' in str(er):
                    error_string = "Правообладатель запретил доступ к данному аудиофайлу. Загрузка прервана"
                vk.messages.send(peer_id=self.user_id, message=error_string, reply_to=self.msg_id, random_id=get_random_id())
                logger.debug(f"Worker-{self.n} [ERROR]: {er}")

            finally:
                #удаление загруженного файла
                if os.path.isfile(self.path): 
                    os.remove(self.path)
                    logger.debug(f"Worker-{self.n} [delete AUDIO file] success: {self.path}") 
                else: 
                    logger.debug(f"Worker-{self.n} [ERROR]: AUDIO file doesn't exist")

                userReqCount.remove(self.user_id)
                logger.debug(f'Worker-{self.n} finish task {options}')
                logger.debug(f"Worker-{self.n} [CURRENT USER QUEUE] {self.user_id}: {userReqCount.count(self.user_id)}")
                logger.debug(f"Worker-{self.n} [CURRENT WORKER QUEUE]: {self._queue.qsize()}")
                

class VkBotWorker():
    def __init__(self):
        self.longpoll = MyVkBotLongPoll(vk_session, '212269992')
        self.queueUsers = Queue()
        threads = []
        for i in range(MAX_WORKERS):
            threads.append(threading.Thread(target=AudioWorker(i, self.queueUsers).start_handling))
            threads[i].start()

    def listen_longpoll(self):
        for event in self.longpoll.listen():
            if event.type == VkBotEventType.MESSAGE_NEW:
                user_id = event.obj.message.get('peer_id')
                message_id = event.obj.message.get('id')

                options = list(filter(None, event.obj.message.get('text').split('\n')))
                logger.debug(f"[new message]: {options}")

                if userReqCount.count(user_id) == MAX_REQUESTS_QUEUE:
                    vk.messages.send(peer_id=user_id, message="Ваше количество запросов в общей очереди не может быть больше {0}!".format(MAX_REQUESTS_QUEUE), random_id=get_random_id())
                else:
                    if not options:
                        attachment_info = event.obj.message.get('attachments')
                        logger.debug(f"[server] attachments info: {len(attachment_info)}, {attachment_info[0].get('type')}")
                        if len(attachment_info) != 1:
                            logger.debug(f"[server] attachment length: {len(attachment_info)}")
                            vk.messages.send(peer_id=user_id, message="Прикреплено больше одного видео!", reply_to=message_id, random_id=get_random_id())
                            continue
                        if attachment_info[0].get('type') != "video":
                            logger.debug(f"[server] attachment type: {attachment_info[0].get('type')}")
                            vk.messages.send(peer_id=user_id, message="Необходимо прикрепить видео!", reply_to=message_id, random_id=get_random_id())
                            continue
                        
                        try:
                            video_info = attachment_info[0].get('video')
                            video_owner_id = video_info.get('owner_id')
                            video_id = video_info.get('id')
                            video = f'{video_owner_id}_{video_id}'
                            logger.debug(f"[server] attachment video: {video}")
                            response = vk_user.video.get(videos=video)
                            options.append(response.get('items')[0].get('player'))
                        except Exception as er:
                            logger.debug(f"[ERROR attachment] {er}")
                            vk.messages.send(peer_id=user_id, message="Невозможно обработать запрос!", reply_to=message_id, random_id=get_random_id())
                            continue

                    elif len(options) > 5:
                        vk.messages.send(peer_id=user_id, message="Слишком много аргументов!", reply_to=message_id, random_id=get_random_id())
                        continue

                    userReqCount.append(user_id)
                    vk.messages.send(peer_id=user_id, message="Запрос добавлен в очередь ({0}/{1})".format(userReqCount.count(user_id), MAX_REQUESTS_QUEUE), random_id=get_random_id())
                    options.insert(0, message_id)
                    options.insert(0, user_id)
                    self.queueUsers.put(options)


            elif event.type != VkBotEventType.MESSAGE_EDIT:
                logger.debug(f"[server] {event.type}")
                

if __name__ == '__main__':
    logger.debug(f"[server] Current version 1.0.1.2")
    logger.debug(f"[server] Filesystem encoding: {sys.getfilesystemencoding()}")
    logger.debug(f"[server] Preferred encoding: {locale.getpreferredencoding()}")
    vkBotWorker = VkBotWorker()
    vkBotWorker.listen_longpoll()
