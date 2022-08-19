#!/usr/bin/env bash
# -*- coding: utf-8 -*-

#Объявление переменных
args=""
version=""
debug_mode=false
container_name="vkbot_container"
#Получение значения версии
while getopts v:d flag
do
	case "${flag}" in
		v) version=${OPTARG};;
		d) debug_mode=true;;
		*) echo "Invalid option: -$flag";;
	esac
done
#Проверка на статус режима отладки
if [ "$debug_mode" = true ]; then
	container_name="vkbot_debug_container"
	version="vDebug"
	args="--debug "
fi
#Проверка на наличие версии, в случае отсутсвия — заверешение
if [ -z "$version" ]; then
	echo 'ERROR: Version is empty! Set it with argument "-v, --version"'
	exit 1
fi

args+='--version "$version"'

#Удаление старого контейнера
echo "Update in progress."
docker rm --force "$container_name"
docker build -t "$container_name" .
docker rmi $(docker images --filter "dangling=true" -q --no-trunc)
#Запуск нового контейнера
echo "Docker: starting up $container_name..."
docker run --env-file /root/AudioBridge-data/.env --volume /root/AudioBridge-data:/var/lib/AudioBridge-sql --name "$container_name" --detach "$container_name" args

echo "Docker status:"
echo "$(docker ps)"
echo "$(docker images)"
