#!/bin/sh

mkdir ~/sox-14.4.2
cd ~/sox-14.4.2
yum -y install wget gcc-c++ libmad libmad-devel libid3tag libid3tag-devel lame lame-devel flac-devel libvorbis-devel
wget https://nchc.dl.sourceforge.net/project/sox/sox/14.4.2/sox-14.4.2.tar.gz
tar -xvzf sox-14.4.2.tar.gz -C ..
./configure --disable-openmp
make -s
make install
