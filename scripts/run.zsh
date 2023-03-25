#!/usr/bin/env bash
# -*- coding: utf-8 -*-

set -e
# Any subsequent(*) commands which fail will cause the shell script to exit immediately


echo 'Starting up Docker container...'

root_dir=$(dirname $PWD)
container_name="vkbot_container"

echo "Debug: Working in \"$(pwd)\"; root dir: \"${root_dir}\"."

#docker run -w root_dir --name $container_name --detach $container_name

if [ ! "$(docker ps -q -f name=$container_name)" ]; then
    echo "Docker: Container \"${container_name}\" is not running."
    if [ "$(docker ps -aq -f status=exited -f name=$container_name)" ]; then
        echo "Docker: Container \"${container_name}\" is exited. Started."
        docker run -w root_dir -detach $container_name --name $container_name
        exit 1
    else
        echo 'Debug: Reached docker ps (2).'
    fi
else
echo "Warning: Docker container \"${container_name}\" already running!"
fi

#echo "cleaning up..."
#docker rm --force $container_name
#docker run -w . -detach $container_name --name $container_name

echo "Docker status:"
echo "$(docker ps)"
echo "$(docker images)"

exit 1
