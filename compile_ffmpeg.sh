#!/bin/bash
BUILD="$(pwd)/build"
mkdir $BUILD
PREFIX="/usr/local/ffmpeg"
BINDIR="/usr/local/ffmpeg/bin"
mkdir -p $PREFIX

echo "export PATH=$PATH:/usr/local/ffmpeg/bin" >> .bashrc

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
  --enable-nonfree \
  --enable-x11grab
make
make install
make distclean
