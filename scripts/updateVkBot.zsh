#!/usr/bin/env bash
# -*- coding: utf-8 -*-

echo 'Update in progress.'
docker rm --force vkbot
docker build -t vkbot .
docker rmi $(docker images --filter "dangling=true" -q --no-trunc)
./runVkBot
echo 'Update done.'

