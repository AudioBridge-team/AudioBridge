#!/usr/bin/env bash
# -*- coding: utf-8 -*-

echo 'Docker: starting up...'
docker run --env-file ../AudioBridge_volumes/.env --name vkbot_container -d vkbot_container

