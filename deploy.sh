#!/bin/bash
#Script for Ubuntu 14.04

#Install RabbitMQ for Celery, Then Celery and MediaInfo wrapper for python
sudo apt-get install rabbitmq-server python-pip mediainfo python-lxml python-dev
sudo pip install celery pymediainfo
#Compile Manually MP4Box from GPAC project
./compile_MP4Box.sh

#Compile FFmpeg
./compile_ffmpeg.sh
