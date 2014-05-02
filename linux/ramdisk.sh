#!/bin/bash
#
# Create a 1GB RAM disk in Linux and start a shell with TMPDIR
# rooted on the ram disk.
#

RPATH="/mnt/ramdisk"

if [ ! -d "$RPATH" ]; then
    sudo mkdir $RPATH
fi

mount | grep -q $RPATH
if [ $? != 0 ]; then
    sudo mount -t tmpfs -o size=1024m tmpfs $RPATH
fi

TMPDIR=$RPATH bash

sudo umount $RPATH
