#!/usr/bin/env bash
# -*- coding: utf-8 -*-

#Объявление переменных
ARGS=""
VERSION=""
DEBUG=false
CONTAINER_NAME="vkbot_container"
#Получение значения версии
while getopts v:d flag
do
	case "${flag}" in
		v) VERSION=${OPTARG};;
		d) DEBUG=true;;
		*) echo "Invalid option: -$flag";;
	esac
done

#Проверка на наличие версии, в случае отсутсвия — заверешение
if [ -z "$VERSION" ]; then
	echo 'ERROR: version is empty! Set it with argument "-v, --version"'
	exit 1
fi

if [ "$DEBUG" = true ]; then
	CONTAINER_NAME+="-$VERSION"
fi

#Удаление старого контейнера
echo "Update in progress."
docker rm --force "$CONTAINER_NAME"
docker build -t "$CONTAINER_NAME" .
docker rmi $(docker images --filter "dangling=true" -q --no-trunc)
#Запуск нового контейнера
echo "Docker: starting up $CONTAINER_NAME..."

if [ "$DEBUG" = true ]; then
	echo "Mode: debug"
	docker run --env-file /root/AB-data/.env --add-host=database:172.17.0.1 --name "$CONTAINER_NAME" --detach "$CONTAINER_NAME" --version "$VERSION" --debug
else
	echo "Mode: release"
	docker run --env-file /root/AB-data/.env --add-host=database:172.17.0.1 --name "$CONTAINER_NAME" --detach "$CONTAINER_NAME" --version "$VERSION"
fi

echo "Docker status:"
echo "$(docker ps)"
echo "$(docker images)"
