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

ACCESS_TOKEN = ''
vk_session_music = vk_api.VkApi(token=ACCESS_TOKEN)
upload = vk_api.VkUpload(vk_session_music)

vk_session = vk_api.VkApi(token='')
longpoll = VkBotLongPoll(vk_session, '212269992')
vk = vk_session.get_api()

MAX_FILESIZE = 200 * 1024 * 1024
MSG_PERIOD = 10
MAX_QUEUE = 5

queue = []

def currentTime():
    return datetime.now().strftime("%d-%m-%Y %H:%M:%S")

class CustomError(Exception):
    def __init__(self, text):
        self.txt = text

def uploadingAudio(user_obj, options):
    counter = -1
    progress_msg_id = ""
    msg_id = user_obj.get('id')
    user_id = user_obj.get('peer_id')
    path = ''
    downloadString = 'youtube-dl --newline --id --extract-audio --audio-quality 0 --audio-format mp3 {0}'.format(options[0])
    try:
        videoString = 'youtube-dl --get-duration {0}'.format(options[0])
        proc = subprocess.Popen(videoString, stdout=subprocess.PIPE, text=True, shell=True)
        video_duration = str(proc.stdout.readline()).strip()
        if len(video_duration) > 5: 
            time_obj = datetime.strptime(video_duration, '%H:%M:%S')
            if time_obj.hour > 2:
                raise CustomError("Длительность youtube видео превышает 2 часа!")

        proc = subprocess.Popen(downloadString, stdout=subprocess.PIPE, text=True, shell=True)
        line = str(proc.stdout.readline()).strip()
        while line:
            if 'Destination' in line and '.mp3' in line:
                path = line[line.find(':')+2:len(line)]
                print(f"{currentTime()} [PATH]: {path}")
            if ' of ' in line:
                if counter == -1:
                    progress_msg_id=vk.messages.send(peer_id=user_id, message="Загрузка началась...", reply_to=msg_id, random_id=get_random_id())
                if counter == MSG_PERIOD:
                    progress = line[line.find(' '):line.find('KiB/s')+5]
                    vk.messages.edit(peer_id=user_id, message=progress, message_id=progress_msg_id)
                    counter = 0
                if ' in ' in line:
                    progress = line[line.find(' '):len(line)]
                    vk.messages.edit(peer_id=user_id, message=progress, message_id=progress_msg_id)
                counter += 1
            line = str(proc.stdout.readline()).strip()  

        if not path:
            raise CustomError("Невалидный URL youtube видео!")

        if os.path.getsize(path) > MAX_FILESIZE:
            raise CustomError("Размер аудиозаписи превышает 200 Мб!")
        else:
            artist = 'undefined'
            title = 'undefined'
            if len(options) == 1:
                videoString = 'youtube-dl --get-title {0}'.format(options[0])
                proc = subprocess.Popen(videoString, stdout=subprocess.PIPE, text=True, shell=True)
                file_name = str(proc.stdout.readline()).strip()
                if file_name: title = file_name
            elif len(options) == 2:
                title = options[1]
            elif len(options) == 3:
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
        print('{0} [CUSTOM ERROR]: {1}'.format(currentTime(), er))
        pass

    except Exception as er:
        vk.messages.send(peer_id=user_id, message="Невозможно загрузить, попробуйте повторить запрос...", reply_to=msg_id, random_id=get_random_id())
        print('{0} [ERROR]: {1}'.format(currentTime(), er))
        pass
    finally:
        if os.path.isfile(path): 
            os.remove(path)
            print(f"{currentTime()} [delete file] success: {path}") 
        else: 
            print(f"{currentTime()} [delete file] error: {path}")
        queue.remove(user_id)
        print(f"{currentTime()} [CURRENT QUEUE] {user_id}: {queue.count(user_id)}") 

def main():
    for event in longpoll.listen():
        if event.type == VkBotEventType.MESSAGE_NEW:
            user_id = event.obj.message.get('peer_id')
            message_id = event.obj.message.get('id')
            options = list(filter(None, event.obj.message.get('text').split('\n')))
            print(f"{currentTime()} [new message]: {options}")
            print(f"{currentTime()} [from]: {user_id}")
            if queue.count(user_id) == MAX_QUEUE:
                vk.messages.send(peer_id=user_id, message="Ваша очередь запросов не может быть больше {0}!".format(MAX_QUEUE), random_id=get_random_id())
            else:
                if len(options) > 3 or not options:
                    vk.messages.send(peer_id=user_id, message="Неверный формат запроса! (возможно, вы прикрепили видео вместо ссылки на видео)", reply_to=message_id, random_id=get_random_id())
                else:
                    queue.append(user_id)
                    vk.messages.send(peer_id=user_id, message="Запрос добавлен в очередь ({0}/{1})".format(queue.count(user_id), MAX_QUEUE), random_id=get_random_id())
                    thread = threading.Thread(target=uploadingAudio, args=(event.obj.message, options)).start()
                    print(f"{currentTime()} [thread] Created new thread. Active extra threads: {threading.active_count() - 1}")

        elif event.type == VkBotEventType.GROUP_JOIN:
            print(f"{currentTime()} [server] New subscriber: {event.obj.user_id}")

        elif event.type != VkBotEventType.MESSAGE_EDIT:
            print(f"{currentTime()} [server] {event.type}")

if __name__ == '__main__':
    print(f"{currentTime()} [server] Filesystem encoding: {sys.getfilesystemencoding()}")
    print(f"{currentTime()} [server] Preferred encoding: {locale.getpreferredencoding()}")
    main()