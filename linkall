#!/bin/bash
#
# Copyright (C) 2011 Nathan Fiedler
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

# Shell script to create symbolic links for all files found in a given directory.
# Links are created in the current working directory.

if [ -z "$1" ]; then
    echo "Missing required directory argument!"
    exit
fi

DIR=$1

for FILE in `find $DIR -type f -print`; do
    ln -s $FILE
done
