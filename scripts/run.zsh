#!/usr/bin/env bash
# -*- coding: utf-8 -*-

set -euo pipefail  # Включаем строгий режим: завершение при ошибках, неопределенных переменных и ошибках в пайпах

echo 'Starting up Docker container...'

readonly root_dir=$(dirname "$PWD")  # Используем readonly для неизменяемых переменных
readonly container_name="vkbot_container"

echo "Debug: Working in \"$(pwd)\"; root dir: \"${root_dir}\"."

# Проверяем, запущен ли контейнер
if docker ps -q -f name="${container_name}" > /dev/null; then
    echo "Warning: Docker container \"${container_name}\" is already running!"
    exit 0  # Выходим, если контейнер уже запущен
fi

# Проверяем, существует ли контейнер, но остановлен
if docker ps -aq -f status=exited -f name="${container_name}" > /dev/null; then
    echo "Docker: Container \"${container_name}\" is stopped. Starting it..."
    docker start "${container_name}"  # Запускаем существующий контейнер
else
    echo "Docker: Container \"${container_name}\" does not exist. Creating and starting it..."
    docker run -d --name "${container_name}" -w "${root_dir}" "${container_name}"  # Создаем и запускаем новый контейнер
fi

echo "Docker status:"
docker ps  # Показываем статус контейнеров
docker images  # Показываем список образов

exit 0  # Успешное завершение скрипта
