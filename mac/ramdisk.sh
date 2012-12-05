#!/bin/bash
#
# Set up a RAM disk and have it be the temporary "disk".
# (add the following to ~/.profile)
#

RDISK=/Volumes/RamDisk
mount | grep -q $RDISK
if [ $? == 1 ]; then
    # Create a ~1GB RAM disk, formatted as HFS+
    DEV=`hdiutil attach -nomount ram://2100000`
    diskutil erasevolume HFS+ "RamDisk" $DEV
fi
if [ -d $RDISK ]; then
    # FYI, TMPDIR is set via launchd_core_logic.c
    declare -x TMPDIR=$RDISK
fi
