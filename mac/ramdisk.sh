#!/bin/bash
#
# Script that performs several tasks:
#
# 1. Set up a 1 GB RAM disk
# 2. Spawn child shell process with TMPDIR set to RAM disk
# 3. Eject RAM disk when child shell exits
#

RNAME='RamDisk'
RPATH="/Volumes/${RNAME}"

# Check if already mounted
mount | grep -q $RPATH
if [ $? == 0 ]; then
    DEV=`mount | grep $RPATH | cut -d ' ' -f 1`
    echo "Using existing RAM disk ${DEV}..."
else
    # Create a ~1GB RAM disk, formatted as HFS+
    DEV=`hdiutil attach -nomount ram://2100000`
    diskutil erasevolume HFS+ $RNAME $DEV
fi

# Start child shell
TMPDIR=$RPATH bash

# Remove the RAM disk when the process exits
diskutil eject $DEV
