#!/bin/bash
#
# Change the Terminal.app tab title.
# Also can change title in Terminal.app via the inspector.
#
# Usage: title.sh <title>
#

if [ "$1" == "" ]; then
    echo 'Missing window title!'
    exit 1
fi

echo -n -e "\033]0;$1\007"
