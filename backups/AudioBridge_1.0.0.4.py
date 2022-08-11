import logging
from logging import StreamHandler, Formatter
import queue
import datetime
from datetime import datetime
import os
import sys
import locale
import threading
import subprocess
import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.utils import get_random_id
from pydub import AudioSegment

ACCESS_TOKEN = ''
vk_session_music = vk_api.VkApi(token=ACCESS_TOKEN)
upload = vk_api.VkUpload(vk_session_music)

vk_session = vk_api.VkApi(token='')
vk = vk_session.get_api()

logger = logging.getLogger("logger")
logger.setLevel(logging.DEBUG)
handler = StreamHandler(stream=sys.stdout)
handler.setFormatter(Formatter(fmt='%(asctime)s: %(message)s'))
logger.addHandler(handler)

MAX_FILESIZE = 200 * 1024 * 1024
MSG_PERIOD = 10
MAX_QUEUE = 5
MAX_USERS_QUEUE = 4
MAX_VIDEO_DURATION = 2 * 60 * 60 * 1000

queueUsers = []
qDict = {}

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

def getMilliseonds(strTime):
    strTime = strTime.strip()
    try:
        pattern = ''
        if strTime.count(":") == 1:
            pattern = '%M:%S'
        if strTime.count(":") == 2:
            pattern = '%H:%M:%S'
        if pattern:
            time_obj = datetime.strptime(strTime, pattern)
            return time_obj.hour * 60 * 60 * 1000 + time_obj.minute * 60 * 1000 + time_obj.second * 1000
        else:
            return int(strTime) * 1000
    except Exception as er:
        logger.debug(f"[server] {er}")
        return -1

def uploadingAudio(user_id):
    while queueUsers.count(user_id):
        qReq = qDict.get(user_id)
        if not qReq:
            logger.debug(f"[server ERROR] Empty qReq, but qUser =", queueUsers.count(user_id))
            for item in queueUsers: 
                if item == user_id: 
                    queueUsers.remove(user_id)
            logger.debug(f"[server ERROR] Clearing qUser =", queueUsers.count(user_id))
            break

        counter = -1
        progress_msg_id = ""
        path = ''

        options = qReq.get()
        msg_id = options.pop(0)
        downloadString = 'youtube-dl -r 5M --newline --id --extract-audio --audio-quality 0 --audio-format mp3 {0}'.format(options[0])
        try:
            if len(options) > 3:
                startTime = getMilliseonds(options[3])
                if startTime == -1:
                    raise CustomError("Неверный формат времени среза!")
                endTime = -1
                if len(options) == 5:
                    endTime = getMilliseonds(options[4])

            videoString = 'youtube-dl --get-duration {0}'.format(options[0])
            proc = subprocess.Popen(videoString, stdout=subprocess.PIPE, text=True, shell=True)
            video_duration = getMilliseonds(str(proc.stdout.readline()))
            if video_duration == -1:
                raise CustomError("Невалидный URL youtube видео!")
            elif video_duration > MAX_VIDEO_DURATION:
                raise CustomError("Длительность youtube видео превышает 2 часа!")

            proc = subprocess.Popen(downloadString, stdout=subprocess.PIPE, text=True, shell=True)
            line = str(proc.stdout.readline())
            while line:
                if 'Destination' in line and '.mp3' in line:
                    path = line[line.find(':')+2:len(line)].strip()
                    logger.debug(f"[PATH]: {path}")
                if ' of ' in line:
                    if counter == -1:
                        progress_msg_id=vk.messages.send(peer_id=user_id, message="Загрузка началась...", reply_to=msg_id, random_id=get_random_id())
                    if counter == MSG_PERIOD:
                        progress = line[line.find(' '):line.find('KiB/s')+5].strip()
                        if progress: vk.messages.edit(peer_id=user_id, message=progress, message_id=progress_msg_id)
                        counter = 0
                    if ' in ' in line:
                        progress = line[line.find(' '):len(line)].strip()
                        if progress: vk.messages.edit(peer_id=user_id, message=progress, message_id=progress_msg_id)
                    counter += 1
                line = str(proc.stdout.readline()) 

            if not path:
                raise CustomError("Невалидный URL youtube видео!")

            if os.path.getsize(path) > MAX_FILESIZE:
                raise CustomError("Размер аудиозаписи превышает 200 Мб!")
            else:
                if len(options) > 3:
                    logger.debug(f"[server] Creating segment...")
                    progress_msg_id=vk.messages.send(peer_id=user_id, message="Создание аудиофрагмента", reply_to=msg_id, random_id=get_random_id())
                    audioSegment = AudioSegment.from_mp3(path)
                    segment = audioSegment[startTime:endTime]
                    segment.export(path, format="mp3")

                artist = 'undefined'
                title = 'undefined'
                if len(options) == 1:
                    videoString = 'youtube-dl --get-title {0}'.format(options[0])
                    proc = subprocess.Popen(videoString, stdout=subprocess.PIPE, text=True, shell=True)
                    file_name = str(proc.stdout.readline()).strip()
                    if file_name: title = file_name
                elif len(options) == 2:
                    title = options[1]
                else:
                    artist = options[2]
                    title = options[1]
                if len(title) > 50: title[0:51]
                
                audio_obj = upload.audio(path, artist, title)
                audio_id = audio_obj.get('id')
                audio_owner_id = audio_obj.get('owner_id')
                attachment = 'audio{0}_{1}'.format(audio_owner_id, audio_id)
                vk.messages.send(peer_id=user_id, attachment=attachment, reply_to=msg_id, random_id=get_random_id())
        except CustomError as er:
            vk.messages.send(peer_id=user_id, message=er, reply_to=msg_id, random_id=get_random_id())
            logger.debug(f"[CUSTOM ERROR]: {er}")

        except Exception as er:
            error_string = "Невозможно загрузить, попробуйте повторить запрос..."
            if '[270]' in str(er):
                error_string = "Правообладатель запретил доступ к данному аудиофайлу. Загрузка прервана"
            vk.messages.send(peer_id=user_id, message=error_string, reply_to=msg_id, random_id=get_random_id())
            logger.debug(f"[ERROR]: {er}")

        finally:
            if os.path.isfile(path): 
                os.remove(path)
                logger.debug(f"[delete file] success: {path}") 
            else: 
                logger.debug(f"[delete file] error: {path}")
            queueUsers.remove(user_id)
            if not queueUsers.count(user_id):
                del qDict[user_id]
            else:
                qDict[user_id] = qReq
            logger.debug(f"[CURRENT QUEUE] {user_id}: {queueUsers.count(user_id)}") 

class VkBotWorker():
    def __init__(self):
        self.longpoll = MyVkBotLongPoll(vk_session, '212269992')

    def listen_longpoll(self):
        for event in self.longpoll.listen():
            if event.type == VkBotEventType.MESSAGE_NEW:
                user_id = event.obj.message.get('peer_id')
                message_id = event.obj.message.get('id')
                options = list(filter(None, event.obj.message.get('text').split('\n')))
                logger.debug(f"[new message]: {options}")
                logger.debug(f"[from]: {user_id}")
                if queueUsers.count(user_id) == MAX_QUEUE:
                    vk.messages.send(peer_id=user_id, message="Ваша очередь запросов не может быть больше {0}!".format(MAX_QUEUE), random_id=get_random_id())
                else:
                    if len(options) > 5 or not options:
                        vk.messages.send(peer_id=user_id, message="Неверный формат запроса! (возможно, вы прикрепили видео вместо ссылки на видео)", reply_to=message_id, random_id=get_random_id())
                    else:
                        queueUsers.append(user_id)
                        vk.messages.send(peer_id=user_id, message="Запрос добавлен в очередь ({0}/{1})".format(queueUsers.count(user_id), MAX_QUEUE), random_id=get_random_id())
                        options.insert(0, message_id)
                        if(queueUsers.count(user_id) == 1):
                            qRequests = queue.Queue()
                            qRequests.put(options)
                            qDict[user_id] = qRequests
                            thread = threading.Thread(target=uploadingAudio, args=(user_id,)).start()
                            logger.debug(f"[thread] Created new thread. Active extra threads: {threading.active_count() - 1}")
                        else:
                            qRequests = qDict.get(user_id)
                            if qRequests:
                                logger.debug(f"[server] append request")
                                qRequests.put(options)
                                qDict[user_id] = qRequests
                            else:
                                logger.debug(f"[server error] can't append request")

            elif event.type == VkBotEventType.GROUP_JOIN:
                logger.debug(f"[server] New subscriber: {event.obj.user_id}")

            elif event.type != VkBotEventType.MESSAGE_EDIT:
                logger.debug(f"[server] {event.type}")

if __name__ == '__main__':
    logger.debug(f"[server] Current version 1.0.0.4")
    logger.debug(f"[server] Filesystem encoding: {sys.getfilesystemencoding()}")
    logger.debug(f"[server] Preferred encoding: {locale.getpreferredencoding()}")
    vkBotWorker = VkBotWorker()
    vkBotWorker.listen_longpoll()