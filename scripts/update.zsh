#!/usr/bin/env bash
# -*- coding: utf-8 -*-

set -euo pipefail  # Включаем строгий режим: завершение при ошибках, неопределенных переменных и ошибках в пайпах

echo 'Update in progress.'

readonly run_script="run.zsh"
readonly root_dir=$(dirname "$PWD")
readonly container_name="vkbot_container"

# Проверка и установка прав на выполнение скрипта
if ! [ -x "${run_script}" ]; then
    echo "Warning: Script \"${run_script}\" is not executable, applying chmod..."

    if [ "$USER" != "root" ]; then
        echo "Fatal: Current user is not root. Can't apply chmod."
        exit 1
    fi

    chmod +x "$run_script"
    echo "Chmod applied."
fi

echo "Script \"${run_script}\" - OK, killing Docker container..."

# Убиваем и удаляем контейнер, если он запущен
if docker ps -q -f name="$container_name" > /dev/null; then
    echo "Stopping and removing container \"${container_name}\"..."
    if docker rm --force "$container_name" > /dev/null; then
        echo "Container \"${container_name}\" was killed and removed."
    else
        echo "Error: Failed to kill and remove container \"${container_name}\"."
        exit 1
    fi
else
    echo "Warning: Docker container \"${container_name}\" is not running."
fi

# Сборка Docker-образа
echo "Docker container killed, (re)building..."
if docker build -t "$container_name" "$root_dir"; then
    echo "(Re)building - OK."
else
    echo "Error: Failed to build Docker image."
    exit 1
fi

# Удаление dangling images
echo "Removing dangling images from the host node..."
dangling_images=$(docker images --filter "dangling=true" -q --no-trunc)
if [ -n "$dangling_images" ]; then
    echo "Found dangling images:"
    echo "$dangling_images"
    docker rmi --force "$dangling_images"
    echo "Dangling images removed."
else
    echo "No dangling images found."
fi

echo "Update done."

# Запуск скрипта
echo "Executing run script..."
if ./"$run_script"; then
    echo "Run script executed successfully."
else
    echo "Error: Run script failed."
    exit 1
fi

exit 0  # Успешное завершение скрипта
