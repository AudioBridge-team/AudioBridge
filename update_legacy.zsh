#!/usr/bin/env bash
# -*- coding: utf-8 -*-

echo 'Update in progress.'
docker rm --force vkbot_container
docker build -t vkbot_container .
docker rmi $(docker images --filter "dangling=true" -q --no-trunc)
./run_legacy.zsh
echo 'Update done.'

