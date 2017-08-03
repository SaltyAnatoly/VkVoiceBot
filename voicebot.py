# -*- coding: utf-8 -*-

import time
import os
import re
import requests
import random
import json
import subprocess
import urllib.request
import shutil
from pydub import AudioSegment
import speech_recognition as sr
from gtts import gTTS
import vk_api

scriptpath = os.path.dirname(__file__) # Путь к скрипту
reg = re.compile('[^a-zA-Z0-9а-яА-ЯёЁ.,!?/ ]') # RegExp для удаления лишних символов из текстового сообщения
vk = vk_api.VkApi(token = 'your_token') # Токен Vk Api
vk.auth() # Авторизация
values = {'out' : 0, 'count' : 100, 'time_offset' : 60} # Данные для обновления информации о входящих сообщениях
rec = sr.Recognizer() # Распознаватель речи
          
def send_voice(user_id, attachments, i):
    msg_url = None # Перемнная для хранения ссылки на аудио-файл голосового сообщения
    path = scriptpath + '/' + str(i); # Путь к аудио-файлу (без расширения)

    # Выдёргиваем линк на аудио
    for a in attachments:
        if a['type'] == 'doc':
            if a['doc']['type'] == 5 and a['doc']['title'] == 'Audio Message':
                msg_url = a['doc']['preview']['audio_msg']['link_ogg']
                break

    # Если не получили ссылку на аудио-файл - выходим из функции
    if not msg_url:
        return
    else:
        # Если получили - скачиваем аудио
        with urllib.request.urlopen(msg_url) as response, open(path + '.ogg', 'wb') as out_file:
            shutil.copyfileobj(response, out_file)
    
    # Конвертируем .ogg в .flac (так хочет гугл)
    AudioSegment.from_file(path + '.ogg', format='ogg').export(path + '.flac', format='flac')

    # Создаём переменную, которую требует передать фунция распознания речи
    with sr.AudioFile(path + '.flac') as source:
        audio = rec.record(source)
    
    try:    
        msg_text = rec.recognize_google(audio, language="ru_RU") # Распознаём речь

        tts = gTTS(text=msg_text, lang='ru') # Отправляем распознанный текст на синтезацию  //Тут ошибка HTTPS
        tts.save(path + '.ogg') # Сохраняем .ogg файл с синтезированной речью

        # Получаем информацию для загрузки аудио-сообщения
        uploading_info = vk.method('docs.getWallUploadServer', {'group_id' : 'group_id', 'type':'audio_message'}) 
        files = {'file': open(path + '.ogg', 'rb')} # Открываем наш аудио-файл для отправки на сервер
        url = uploading_info['upload_url'] # Выдёргиваем URL
        # Получаем нужную информацию для сохранения файла на сервере ВК
        req = json.loads(requests.post(url, files=files).text.replace("'", "\\"))['file'] 
        uploaded_doc_info = vk.method('docs.save', {'file':req}) # Загружаем файл на сервер
        owner_id, media_id = uploaded_doc_info[0]['owner_id'], uploaded_doc_info[0]['id'] # Получаем id файла и его владельца
        attachment = 'doc' + str(owner_id) + '_' + str(media_id) # Создаём строку, которую нужно передать в сообщении
        vk.method('messages.send', {'user_id':user_id, 'attachment': attachment}) # Отправляем голосовое сообщение

        print('================================================================================')
        print('Время: ' + time.asctime())
        print('Сообщение отправлено следующему пользователю: ' + str(user_id))
        print('Текст озвученного сообщения: ' +  msg_text)
    except sr.UnknownValueError:
        print("Ошибка распознания")
    except sr.RequestError as e:
        print("Не удалось получить ответ от сервера Google: {0}".format(e))
    
def main():
    i = 0 # Индекс для именования аудио-файлов
    while True: # Бесконечный цикл
        time.sleep(1) # Задержка
        response = vk.method('messages.get', values) # Получаем список сообщений
        # Смотрим, какием сообщения новые
        if response['items']:
            values['last_message_id'] = response['items'][0]['id']
        #Отвечаем
        for item in response['items']: 
            send_voice(item['user_id'], item['attachments'], i)
            i += 1
    
    
if __name__ == '__main__':
    main()
