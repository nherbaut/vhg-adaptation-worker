# Adaptation and Caching Worker #

## Description ##

One of the key feature of cloud computing is its ability to produce on-demand compute power at a small cost. To take advantage of this feature, we decided to implement the most computing intensive tasks as network of workers using a Python framework called Celery. Celery is an asynchronous task queue/job queue based on distributed message passing.
Every Celery worker is a stand alone application being able to perform one or more tasks in an parallelized manner. To achieve this goal, a general transcoding work flow has been designed to be applied on a remote video file. 

Subtasks 3.1, 3.2, can be run in parallel, leaving the possibility to deploy as many worker as desired to fulfill the needs of performance.
We created a virtual machine template with the appropriate software configuration, letting the VNF Orchestrator dealing with underlaying network connections details. The network topology is flat, every streamer being directly connected to a message a Message Broker.
Having a network of worker allows us to scale-up or scale-down the overall compute power simply by turning a virtual machine up or down. Once the worker is up, it connects to the message broker, and pick up the first task available on the queue. Frequent feedback messages are pushed to the message broker, allowing us to present the results on the gateway as soon as they are available on the storage. 
If the compute capacity is above the required level, active workers are decommissioned, leaving the pool as their host virtual machine turns of.

## installation ##

### ffmpeg & GPAC ###

download and build from source, but before, install necessary pacakges

    sudo apt-get -y install autoconf automake build-essential libgpac-dev libsdl1.2-dev libtheora-dev libtool libva-dev libvdpau-dev libvorbis-dev libx11-dev libxext-dev libxfixes-dev pkg-config texi2html zlib1g-dev yasm libx264-dev libmp3lame-dev libopus-dev libvpx-dev unzip
    mkdir build
    cd build
    wget http://ffmpeg.org/releases/ffmpeg-2.5.tar.bz2
    tar -xvf ./ffmpeg-2.5.tar.bz2 
    cd ffmpeg-2.5/
    ./configure     --enable-gpl       --enable-libtheora   --enable-libvorbis    --enable-libx264   --enable-nonfree   --enable-x11grab
    make
    sudo make install
    cd ..
    wget https://github.com/gpac/gpac/archive/master.zip -O gpack.zip
    unzip gpack.zip 
    cd gpac-master/
    ./configure 
    make
    sudo make install



### Celery on Debian ###

    sudo apt-get install python-pip mediainfo python-dev libxslt1-dev python-dev
    sudo pip install celery pymediainfo lxml pika

### Celery As a Daemon ###

follow instructions given at http://celery.readthedocs.org/en/latest/tutorials/daemonizing.html#generic-init-scripts

### Configuration ###

configuration options are in the settings.py file. You can configure the broker url and default output dir

```python
    BROKER_URL = 'amqp://guest:guest@172.16.1.1' #connection to the message broker
    CELERY_RESULT_BACKEND = 'amqp://guest:guest@172.16.1.1' #that's to connect to result backend
    config = {"folder_out": "/home/nicolas/output", #where the files should be writt en
        "bitrates_size_dict": {100: 100, 200:200}} # what king of transcoding should be done
```

if your worker is called worker 1, logs are located in 

    /var/log/celery/worker1.log

## Running tasks ##

The project is composed from various celery tasks in the adaptation python package. One should only call high level task encoding_workflow in the commons.py module.

### Context ###

The context diict is the only arg that is passed from task task. It has various helper functions that help computing eg. resources path.

### A Task Scenario ###

* A task is given the context by *args
* Some named arguments that are retrieved by **kwargs. 
* All named arguments should be added to the context dict. 
* Context fields should be used in the task business. 
* Context should be returned by the task to be used by the next task.


### Workflow ###
here's a description on how the encoding workflow tasks work. Some long stating task run un parallel on different workers thanks to a celery chord

    _________________   _______________   ____________________
    | DOWNLOAD FILE |___|GET VIDEO SIZE|__|ADD PLAYLIST HEADER|__     
    |_______________|   |______________|  |___________________|  |
                                                                 |
                                                                 |
                                                _________________|________________
                                                | For each couple heigh/bitrate  |\
                                                |    _____________________       | \
                                                |    |COMPUTE TARGET SIZE |      | |\
                                                |    |____________________|      | | \
                                                |              |                 | | |
                                                |    __________|___________      | | |
                                                |    |TRANSCODE 3.1        |     | | |
                                                |    |_____________________|     | | |
                                                |              |                 | | |
                                                |              |                 | | |
                                                |     _________|____________     | | |
                                                |     | CHUNK HLS 3.2      |     | | |
                                                |     |____________________|     | | |
                                                |              |                 | | |
                                                |      ________|____________     | | |
                                                |      |ADD PLAYLIST INFO  |     | | |
                                                |      |___________________|     | | |
                                                |              |                 | | |
                                                |      ________|____________     | | |
                                                |      |NOTIFY STATUS      |     | | |
                                                |      |___________________|     | | |
                                                |________________________________| | |
                                                  \____________|__________________\| |
                                                    \__________|___________________\_|
                                                       ________|___________
                                                       |ADD PLAYLIST FOOTER|
                                                       |___________________|
                                                               |
                                                        _______|___________
                                                        | CHUNK DASH       |
                                                        |__________________|
                                                        _______|___________
                                                        | NOTIFY STATUS    |
                                                        |__________________|


### Notifications ###

Notification task send a json message on the broker with info about the current status of the transcoding. Message is sent to the *tanscode-result* queue.

```json
    {"quality":"medium","main_task_id":"uuid...","complete":False}
```


compile_ffmpeg.sh
==========
```
#!/bin/bash
BUILD="$(pwd)/build"
mkdir $BUILD
PREFIX="/usr/local/"
BINDIR="/usr/local/bin"
mkdir -p $PREFIX

#echo "export PATH=$PATH:/usr/local/ffmpeg/bin" >> .bashrc

apt-get update
apt-get -y install autoconf automake build-essential libass-dev libfreetype6-dev libgpac-dev \
  libsdl1.2-dev libtheora-dev libtool libva-dev libvdpau-dev libvorbis-dev libx11-dev \
  libxext-dev libxfixes-dev pkg-config texi2html zlib1g-dev yasm libx264-dev libfdk-aac-dev libmp3lame-dev libopus-dev libvpx-dev
mkdir ~/ffmpeg_sources

cd $BUILD
wget http://ffmpeg.org/releases/ffmpeg-snapshot.tar.bz2
tar xjvf ffmpeg-snapshot.tar.bz2
cd ffmpeg
PKG_CONFIG_PATH="$PREFIX/lib/pkgconfig" 
./configure \
  --prefix="$PREFIX" \
  --extra-cflags="-I$PREFIX/include" \
  --extra-ldflags="-L$PREFIX/lib" \
  --bindir=$BINDIR \
  --enable-gpl \
  --enable-pic \
  --enable-libass \
  --enable-libfdk-aac \
  --enable-libfreetype \
  --enable-libmp3lame \
  --enable-libopus \
  --enable-libtheora \
  --enable-libvorbis \
  --enable-libvpx \
  --enable-libx264 \
  --enable-nonfree

make
make install
make distclean
```

compile_MP4Box.sh
===========
```
#!/bin/bash



apt-get install subversion make pkg-config g++ zlib1g-dev libfreetype6-dev libjpeg62-dev libpng12-dev libopenjpeg-dev libmad0-dev libfaad-dev libogg-dev libvorbis-dev libtheora-dev liba52-0.7.4-dev libavcodec-dev libavformat-dev libavutil-dev libswscale-dev libavresample-dev libxv-dev x11proto-video-dev libgl1-mesa-dev x11proto-gl-dev linux-sound-base libxvidcore-dev libssl-dev libjack-dev libasound2-dev libpulse-dev libsdl1.2-dev dvb-apps libavcodec-extra libavdevice-dev libmozjs185-dev subversion

svn co svn://svn.code.sf.net/p/gpac/code/trunk/gpac gpac

cd gpac
./configure
make
sudo make install
```

start background
============

#!/bin/bash
celery -A adaptation.commons worker --loglevel=info --concurrency=1 > logs.txt 2>&1 &

