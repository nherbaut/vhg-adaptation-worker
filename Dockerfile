FROM celery:3.1.18
MAINTAINER nherbaut@labri.fr
USER root
RUN apt-get update &&  apt-get -y install autoconf automake build-essential libgpac-dev libsdl1.2-dev libtheora-dev libtool libva-dev libvdpau-dev libvorbis-dev libx11-dev libxext-dev libxfixes-dev pkg-config texi2html zlib1g-dev yasm libx264-dev libmp3lame-dev libopus-dev libvpx-dev unzip python-pip mediainfo python-dev libxslt1-dev python-dev 
run apt-get -y install wget 
RUN mkdir build && cd build && wget http://ffmpeg.org/releases/ffmpeg-2.5.tar.bz2 && tar -xvf ./ffmpeg-2.5.tar.bz2 && cd ffmpeg-2.5/ && ./configure     --enable-gpl       --enable-libtheora   --enable-libvorbis    --enable-libx264   --enable-nonfree   --enable-x11grab && make &&  make install
RUN cd /tmp && wget https://github.com/gpac/gpac/archive/master.zip -O gpack.zip && unzip gpack.zip 
WORKDIR /tmp/gpac-master/
RUN ./configure --use-ffmpeg=no && make &&  make install	
RUN apt-get -y install python-virtualenv
RUN mkdir -p /worker/adaptation
WORKDIR /worker/
RUN virtualenv -p /usr/bin/python2.7 venv
RUN /bin/bash -c "source venv/bin/activate \
    && apt-get -y install python-pip mediainfo python-dev libxslt1-dev python-dev \
    && pip install celery pymediainfo lxml pika \
    && easy_install beautifulsoup4 "
COPY adaptation/ /worker/adaptation
RUN rm -rf /home/user/build
RUN rm -rf /tmp/*
RUN mkdir -p /var/www/in
RUN mkdir -p /var/www/out
RUN chown -R user:user /var/www
RUN /bin/bash -c "source venv/bin/activate \
    && pip install python-swiftclient"
USER user
WORKDIR /worker
CMD /bin/bash -c "source venv/bin/activate \ 
    && celery worker -A adaptation.commons"
