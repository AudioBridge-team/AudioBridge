#!/usr/bin/env bash
# -*- coding: utf-8 -*-

set -euo pipefail  # Включаем строгий режим: завершение при ошибках, неопределенных переменных и ошибках в пайпах

# Объявление переменных
DEV=false
ENV_PATH="/root/AudioBridge/data/.env."

# Получение значения версии
while getopts ":d" flag; do
    case "${flag}" in
        d) DEV=true ;;
        *) echo "Invalid option: -${OPTARG}" >&2
           exit 1 ;;
    esac
done

# Определение режима (dev/prod)
MODE="prod"
if [ "$DEV" = true ]; then
    MODE="dev"
fi

ENV_PATH+="$MODE"

echo "Update in progress..."

# Запуск нового контейнера
MODE=$MODE docker compose --env-file "$ENV_PATH" up --build -d

echo "Clearing old images..."

# Удаление старых образов (dangling images)
if docker images --filter "dangling=true" -q | grep -q .; then
    docker rmi $(docker images --filter "dangling=true" -q --no-trunc)
else
    echo "No dangling images to remove."
fi

echo "Docker status:"
docker ps
docker images

exit 0  # Успешное завершение скрипта
