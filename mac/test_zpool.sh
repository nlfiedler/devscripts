#!/bin/bash
#
# Create a RAM disk and initialize with ZFS.
#

RPATH="/Volumes/tank"

# Check if already mounted
mount | grep -q $RPATH
if [ $? == 0 ]; then
    DEV=`mount | grep $RPATH | cut -d ' ' -f 1`
    echo "Already created at ${DEV}..."
else
    # Create a ~2GB RAM disk, formatted as HFS+
    DEV=`hdiutil attach -nomount ram://4200000`
    # remove trailing whitespace characters
    DEV="${DEV%"${DEV##*[![:space:]]}"}"   # "
    sudo zpool create -m $RPATH tank $DEV
fi

echo "Run 'sudo zpool destroy tank' to delete the pool."
echo "Then run 'diskutil eject $DEV' to delete the RAM disk."
