#!/usr/bin/env bash
# -*- coding: utf-8 -*-

#Получение значения версии
while getopts v: flag
do
	case "${flag}" in
		v) version=${OPTARG};;
	esac
done
#Проверка на наличие версии, в случае отсутсвия — заверешение
if [ -z "$version" ]; then
	echo 'ERROR: Version is empty! Set it with argument "-v"'
	exit 1
fi
#Удаление старого контейнера
echo 'Update in progress.'
docker rm --force vkbot_container
docker build -t vkbot_container .
docker rmi $(docker images --filter "dangling=true" -q --no-trunc)
#Запуск нового контейнера
echo 'Docker: starting up...'
docker run --env-file /root/AudioBridge-data/.env -e VERSION="$version" -v /root/AudioBridge-data:/var/lib/AudioBridge-sql --name vkbot_container -d vkbot_container

echo "Docker status:"
echo "$(docker ps)"
echo "$(docker images)"
