#!/usr/bin/env bash
# -*- coding: utf-8 -*-

set -e
# Any subsequent(*) commands which fail will cause the shell script to exit immediately


echo 'Update in progress.'

run_script="run.zsh"
root_dir=$(dirname $PWD)
container_name="vkbot_container"

if ! [ -x "${run_script}" ]; then
    echo "Warning: Script \"${run_script}\" can't be executed, applying chmod..."
    #if [[ $UID != 0 ] || [ $USER != root ]]; then
    if [ $USER != root ]; then
        echo "${USER} cannot write the file \"${run_script}\"."
        echo "Fatal: I'm not root. Can't use chmod."
        exit 1
    fi
    # sudo -u $USER test -w $run_script || {}
    chmod +x "$run_script"
    echo "Chmod applied."
fi

echo "Script \"${run_script}\" - OK, killing docker container..."
if [ ! "$(docker ps -q -f name=$container_name)" ]; then
    kill_result=$(docker rm --force $container_name) # cleanup
    echo "Debug: kill_result=${kill_result}"
    if ![ $kill_result ]; then
        echo "Container was killed."
    else
        echo "Container was not killed!"
    fi

    if [ "$(docker ps -aq -f status=exited -f name=$container_name)" ]; then
        echo 'Debug: Reached docker ps (1).'
    fi
else
echo "Warning: Docker container was not running!"
fi
echo "Docker container killed, (re)building..."
docker build -t $container_name $root_dir
echo "(Re)building - OK, removing images from the host node:"
echo "$(docker images --filter 'dangling=true')"
docker rmi --force $(docker images --filter "dangling=true" -q --no-trunc)
echo "Removing images - OK, update done."

echo "Executing run script."
# run your container
./run.zsh

#return 1
