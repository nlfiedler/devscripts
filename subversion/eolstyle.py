#!/usr/bin/python
#
# Copyright (c) 2010 Nathan Fiedler
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
# $Id$
#
# Marks source files with the Subversion svn:eol-style property,
# setting the value to "native".
#
# TODO: detect and ignore entries not under Subversion control
#

import os
import os.path
from svn import wc
import sys

# List of filename extensions to be processed.
extensions = [
    'css',
    'html',
    'java',
    'json',
    'properties',
    'py',
    'sh',
    'txt',
    'xml',
    'xsd',
    'yaml'
]

def setprop(file, baton):
    """
    Set the svn:eol-style property to 'native' on the passed file.
    """
    svn_err = wc.prop_set("svn:eol-style", "native", file, baton)
    if svn_err is not None:
        print "Error: %s" % svn_err
        sys.exit(1)

def main():
    # If argument is given, use that as top directory; otherwise use cwd.
    if len(sys.argv) > 1:
        cwd = sys.argv[1]
    else:
        cwd = os.getcwd()
    # Get an access baton for the Subversion working copy.
    adm_baton = wc.adm_open(None, cwd, True, True)
    # Walk the directory tree looking for matching files that are not
    # in Subversion (.svn) directories.
    # Also ignore NetBeans private project data.
    for root, dirs, files in os.walk(cwd):
        for name in files:
            foo, sep, ext = name.rpartition('.')
            if ext.lower() in extensions:
                setprop(os.path.join(root, name), adm_baton)
        if '.svn' in dirs:
            dirs.remove('.svn')
        if 'private' in dirs and root.endswith('nbproject'):
            dirs.remove('private')
    # Close the access baton.
    wc.adm_close(adm_baton)

if __name__ == "__main__":
    main()
