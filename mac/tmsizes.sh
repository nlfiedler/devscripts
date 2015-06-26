#!/bin/bash
#
# Calculate unique sizes of all Time Machine snapshots.
#

BACKUPS=`tmutil listbackups`
for SNAPSHOT in $BACKUPS; do
    sudo tmutil uniquesize $SNAPSHOT
done
