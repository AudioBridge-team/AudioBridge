#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Список ошибок VK API
vkapi_errors = {
    270: "Правообладатель ограничил доступ к данной аудиозаписи. Загрузка прервана",
    15 : "VK отклонил загрузку трека. Точную причину ошибки вы можете узнать у разработчиков",
    100: "Невозможно загрузить аудиофайл из-за ошибки серверов VK. Повторите свой запрос чуть позже",
    10 : "Возникла непредвиденная ошибка со стороны VK. Повторите свой запрос чуть позже",
    9  : "Бот превысил лимит загрузки песен в день. Повторите свой запрос позже"
}