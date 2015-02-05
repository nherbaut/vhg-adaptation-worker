#!/bin/bash



apt-get install subversion make pkg-config g++ zlib1g-dev libfreetype6-dev libjpeg62-dev libpng12-dev libopenjpeg-dev libmad0-dev libfaad-dev libogg-dev libvorbis-dev libtheora-dev liba52-0.7.4-dev libavcodec-dev libavformat-dev libavutil-dev libswscale-dev libavresample-dev libxv-dev x11proto-video-dev libgl1-mesa-dev x11proto-gl-dev linux-sound-base libxvidcore-dev libssl-dev libjack-dev libasound2-dev libpulse-dev libsdl1.2-dev dvb-apps libavcodec-extra libavdevice-dev libmozjs185-dev subversion

svn co svn://svn.code.sf.net/p/gpac/code/trunk/gpac gpac

cd gpac
./configure
make
sudo make install