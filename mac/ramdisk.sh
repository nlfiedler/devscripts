#!/bin/bash
#
# Script that performs the following tasks:
#
# 1. Set up a RAM disk of reasonable size
# 2. Spawn child shell process with TMPDIR set to RAM disk
# 3. Eject RAM disk when child shell exits
#

RNAME='RamDisk'
RPATH="/Volumes/${RNAME}"

#
# Get the size in bytes of the available RAM on this system, then divide by
# 8 and divide that by the sector size (512 bytes) to arrive at the number
# of sectors to be allocated to the RAM disk.
#
let SECTORS=`sysctl -n hw.memsize`/8/512

# Check if already mounted
mount | grep -q $RPATH
if [ $? == 0 ]; then
    DEV=`mount | grep $RPATH | cut -d ' ' -f 1`
    echo "Using existing RAM disk ${DEV}..."
else
    DEV=`hdiutil attach -nomount ram://$SECTORS`
    diskutil erasevolume "Case-sensitive HFS+" $RNAME $DEV
fi

# Start child shell
TMPDIR=$RPATH bash

# Remove the RAM disk when the process exits
diskutil eject $DEV
