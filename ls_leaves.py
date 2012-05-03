#!/usr/bin/env python
#
# Find the leaf directories within the given set of paths
# (defaulting to the current working directory) and display
# the sorted result set.
#

import os
import sys

def main():
    # If arguments are given, use them as a starting point.
    paths = []
    if len(sys.argv) > 1:
        paths = sys.argv[1:]
    else:
        paths.append('.')

    # Walk the directory tree looking for directories with no child directories.
    leaves = []
    for path in paths:
        for root, dirs, files in os.walk(path):
            if len(dirs) == 0:
                if root.startswith('./'):
                    root = root[2:]
                leaves.append(root)

    # Sort the results and output.
    leaves.sort()
    for leaf in leaves:
        print leaf

if __name__ == "__main__":
    main()
