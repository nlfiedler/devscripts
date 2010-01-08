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
# Invoke this script with '--help' option for detailed description of
# what it does and how you can use it.
#
import getopt
import os
import re
import subprocess
import sys

def client():
    """Returns mapping of client view with normalized client paths."""
    #
    # The relevant parts of the client specification are:
    #
    # Client:	myp4client
    # Root:	/Users/me/perforce
    # View:
    #	//depot1/... //myp4client/depot1/...
    #	-//depot2/... //myp4client/depot2/...
    #
    output = subprocess.Popen(["p4", "client", "-o"],
            stdout=subprocess.PIPE).communicate()[0]
    client = None
    root = None
    view = []
    lines = iter(output.splitlines())
    try:
        while True:
            line = lines.next()
            if line.startswith("Client:"):
                client = line.partition(":")[2].strip()
            elif line.startswith("Root:"):
                root = line.partition(":")[2].strip()
            elif line.startswith("View:"):
                line = lines.next()
                while line.startswith("\t"):
                    line = line.strip()
                    # Ignore lines that start with '-' as they have no
                    # bearing on finding missing files.
                    if not line.startswith("-") and len(line) > 0:
                        line = line.replace("/...", "")
                        view.append(line)
                    line = lines.next()
    except StopIteration:
        pass
    # Convert the paths to absolute client paths.
    view = [v.replace("//%s/" % client, "%s/" % root) for v in view]
    # Produce a map of depot paths to client paths.
    map = {}
    for v in view:
        (k, s, v) = v.partition(" ")
        map[k] = v
    return map

def opened(mapping):
    """
    Returns a normalized list of files opened by the client.
    Parameter 'mapping' maps Perforce paths to client paths and is
    used to convert the output of p4 opened into client paths.
    """
    #
    # Typical 'p4 opened' output:
    # //root/path/file#1 - add default change (text)
    #
    output = subprocess.Popen(["p4", "opened"],
            stdout=subprocess.PIPE).communicate()[0]
    lines = output.splitlines()
    # Remove the trailing cruft, leaving only the file names.
    lines = [re.sub("#\d+ - .*$", "", line) for line in lines]
    # Substitute the Perforce path with the client path.
    def normalize(path):
        for k in mapping:
            if path.startswith(k):
                return re.sub(k, mapping[k], path)
        return path
    lines = [normalize(line) for line in lines]
    return lines

def missing():
    """Returns a normalized list of files unknown to Perforce."""
    #
    # The Perforce knowledge base shows the following example.
    #    find . -type f | p4 -x- have > /dev/null
    #
    find = subprocess.Popen(["find", ".", "-type", "f"],
            stdout=subprocess.PIPE)
    p4 = subprocess.Popen(["p4", "-x-", "have"], stdin=find.stdout,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output = p4.communicate()[1]
    lines = output.splitlines()
    cwd = os.getcwd()
    # Remove the trailing cruft, leaving only the file names, and
    # convert them to absolute client paths.
    def normalize(str):
        s = re.sub(" - file\(s\) not on client\.$", "", str)
        return re.sub("^\.", cwd, s)
    lines = [normalize(line) for line in lines]
    return lines

def diff(open, unknown):
    """
    Returns a sorted list of files that are unknown to Perforce and not
    already opened for add. This function assumes that files that are
    opened are also in the cient workspace (i.e. not "missing").
    """
    o = set(open)
    u = set(unknown)
    d = u.difference(o)
    # Where is the built-in to convert an iterable set into a list?
    results = []
    for e in d:
        results.append(e)
    results.sort()
    return results

def usage():
    """Display usage information for this script."""
    print "Display list of files that are not known by Perforce."
    print ""
    print "Usage: p4uknown.py [-h]"
    print ""
    print "-h|--help"
    print "\tPrints this usage information."

def main():
    """The main function for processing user input."""
    # Parse the command line arguments.
    shortopts = "h"
    longopts = ["help"]
    try:
        opts, args = getopt.getopt(sys.argv[1:], shortopts, longopts)
    except getopt.GetoptError, err:
        print str(err)
        print "Invoke with -h for help."
        sys.exit(2)
    for opt, val in opts:
        if opt in ("-h", "--help"):
            usage()
            sys.exit()
        else:
            assert False, "unhandled option: %s" % opt
    # Identify the files unknown to Perforce and display them.
    view = client()
    open = opened(view)
    missed = missing()
    diffs = diff(open, missed)
    if len(diffs) > 0:
        cwd = os.getcwd()
        for m in diffs:
            # Convert the absolute path to a relative one.
            m = re.sub(cwd, ".", m)
            print "? %s" % m

if __name__ == "__main__":
    main()
