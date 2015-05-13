FROM debian:stable
MAINTAINER nherbaut@labri.fr

RUN apt-get update &&  apt-get -y install autoconf automake build-essential libgpac-dev libsdl1.2-dev libtheora-dev libtool libva-dev libvdpau-dev libvorbis-dev libx11-dev libxext-dev libxfixes-dev pkg-config texi2html zlib1g-dev yasm libx264-dev libmp3lame-dev libopus-dev libvpx-dev unzip python-pip mediainfo python-dev libxslt1-dev python-dev 
run apt-get -y install wget 
RUN mkdir build && cd build && wget http://ffmpeg.org/releases/ffmpeg-2.5.tar.bz2 && tar -xvf ./ffmpeg-2.5.tar.bz2 && cd ffmpeg-2.5/ && ./configure     --enable-gpl       --enable-libtheora   --enable-libvorbis    --enable-libx264   --enable-nonfree   --enable-x11grab && make &&  make install
RUN cd .. && wget https://github.com/gpac/gpac/archive/master.zip -O gpack.zip && unzip gpack.zip && cd gpac-master/
RUN cd gpac-master && ./configure --use-ffmpeg=no && make &&  make install
RUN apt-get -y install python-pip mediainfo python-dev libxslt1-dev python-dev
RUN pip install celery pymediainfo lxml pika
VOLUME ["/worker"]
COPY ./vhg_adaptation_worker-0.1-py2.7.egg /worker/
RUN easy_install /worker/vhg_adaptation_worker-0.1-py2.7.egg
CMD export C_FORCE_ROOT=true && celery -A adaptation.commons worker --loglevel=info --concurrency=1
