#!/usr/bin/env bash
# -*- coding: utf-8 -*-

#Объявление переменных
VERSION=""
DEV=false
CONTAINER_NAME="vkbot_container_"
ENV_PATH="/root/AudioBridge/data/.env."
LOGS_PATH="/root/AudioBridge/data/logs"
#Получение значения версии
while getopts v:d flag
do
	case "${flag}" in
		v) VERSION=${OPTARG};;
		d) DEV=true;;
		*) echo "Invalid option: -$flag";;
	esac
done

#Проверка на наличие версии, в случае отсутсвия — заверешение
if [ -z "$VERSION" ]; then
	echo 'ERROR: version is empty! Set it with argument "-v, --version"'
	exit 1
fi

MODE="prod"
if [ "$DEV" = true ]; then
	MODE="dev"
fi
CONTAINER_NAME+="$MODE"
ENV_PATH+="$MODE"

#Удаление старого контейнера
echo "Update in progress."
docker rm --force "$CONTAINER_NAME"
docker build -t "$CONTAINER_NAME" .
docker rmi $(docker images --filter "dangling=true" -q --no-trunc)
#Запуск нового контейнера
echo "Docker: starting up $CONTAINER_NAME..."

if [ "$DEV" = true ]; then
	echo "Mode: dev"
	docker run --env-file "$ENV_PATH" -v "$LOGS_PATH":/AudioBridge/data/logs --add-host=database:172.17.0.1 --name "$CONTAINER_NAME" --detach "$CONTAINER_NAME" --version "$VERSION"
else
	echo "Mode: prod"
	docker run --env-file "$ENV_PATH" -v "$LOGS_PATH":/AudioBridge/data/logs --add-host=database:172.17.0.1 --name "$CONTAINER_NAME" --detach "$CONTAINER_NAME" --version "$VERSION"
fi

echo "Docker status:"
echo "$(docker ps)"
echo "$(docker images)"
