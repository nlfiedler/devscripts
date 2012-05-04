#!/usr/bin/env python
#
# Performs a search and replace on a set of files.
#
# Directories named '.svn' and '.hg' are ignored.
#

import getopt
import os
import os.path
import re
import sys


def main():
    pattern = ""
    replace = ""
    myext = ""

    # parse the command line arguments
    shortopts = "hp:r:e:"
    longopts = ["help", "pattern", "replace", "ext"]
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
        elif opt in ("-p", "--pattern"):
            pattern = val
        elif opt in ("-r", "--replace"):
            replace = val
        elif opt in ("-e", "--ext"):
            myext = val
        else:
            assert False, "unhandled option: %s" % opt

    if pattern == "" or replace == "" or myext == "":
        print "Usage: findrepl.py [options] [<path>]"
        print "Invoke with --help for helpful information"
        sys.exit(0)

    # if argument is given, use that as top directory; otherwise use cwd
    if len(args) > 0:
        cwd = args[0]
    else:
        cwd = os.getcwd()
    # prepare the regex for repeated use
    regex = re.compile(pattern)
    # walk the directory tree looking for matching files
    for root, dirs, files in os.walk(cwd):
        for name in files:
            foo, sep, ext = name.rpartition('.')
            if ext.lower() == myext:
                fname = os.path.join(root, name)
                with open(fname) as f:
                    lines = f.readlines()
                with open(fname, 'w') as f:
                    for line in lines:
                        line = regex.sub(replace, line)
                        f.write(line)
        if '.svn' in dirs:
            dirs.remove('.svn')
        elif '.hg' in dirs:
            dirs.remove('.hg')


def usage():
    print """Usage: findrepl.py [-h] -p <patt> -r <repl> -e <ext> [path]

This script searches the specified directory tree (defaults to cwd) for
files whose extension matches the -e argument, replacing occurrences of
<pattern> with <replacement> within those files.

-h|--help
\tPrints this usage information.

-d|--debug
\tDisplay debugging messages.

-v|--verbose
\tPrints information about what the script is doing at each step.

-p|--pattern <regex>
\tPattern to find in matching files. [Required]

-r|--replace <text>
\tReplacement for the matching patterns. [Required]

-e|--ext <extension>
\tFile name extension to find. [Required]
"""

if __name__ == "__main__":
    main()
