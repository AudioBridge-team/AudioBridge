#!/usr/bin/env bash
# -*- coding: utf-8 -*-

#Объявление переменных
VERSION=""
DEV=false
ENV_PATH="/root/AudioBridge/data/.env."
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
ENV_PATH+="$MODE"
echo "Update in progress."
#Запуск нового контейнера
BUILD_VERSION=$VERSION MODE=$MODE docker compose --env-file $ENV_PATH up --build -d
echo "Clearing old images..."
#Удаление старых образов
docker rmi $(docker images --filter "dangling=true" -q --no-trunc)

echo "Docker status:"
echo "$(docker ps)"
echo "$(docker images)"
