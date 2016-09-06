#!/bin/bash
#
# Script that performs the following tasks:
#
# 1. Set up a RAM disk of reasonable size
# 2. Spawn child shell process with TMPDIR set to RAM disk
# 3. Eject RAM disk when child shell exits
#

#
# Get the size in bytes of the available RAM on this system, then divide by
# 8 and divide that by the sector size (512 bytes) to arrive at the number
# of sectors to be allocated to the RAM disk.
#
let SECTORS=`sysctl -n hw.memsize`/8/512

#
# Create the RAM disk now, if not already created. Otherwise, work out what
# the device identifer and mount point are so we can set the temp dir and
# eventually eject the disk.
#
`diskutil mount RamDisk > /dev/null 2>&1`
if [ $? == 0 ]; then
    echo "Using existing RamDisk..."
else
    DEV=`hdiutil attach -nomount ram://$SECTORS`
    diskutil erasevolume "Case-sensitive HFS+" RamDisk $DEV
fi
DISK_INFO=`diskutil info RamDisk`
DEVICE_NODE=`echo $DISK_INFO | grep 'Device Node:' | awk '{print $3}'`
MOUNT_POINT=`echo $DISK_INFO | grep 'Mount Point:' | awk '{print $3}'`

# Start child shell
TMPDIR=$MOUNT_POINT bash

# Remove the RAM disk when the process exits
diskutil eject $DEVICE_NODE
