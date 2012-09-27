#!/usr/bin/env python3
#
# Counts lines of code in Python scripts. Bascially a fixed version
# of http://code.activestate.com/recipes/527746-line-of-code-counter/
#

import os
import fnmatch


def walk(root='.', recurse=True, pattern='*'):
    """Generator for walking a directory tree. Starts at specified root
    folder, returning files that match our pattern. Optionally will also
    recurse through directories.
    """
    for path, subdirs, files in os.walk(root):
        for name in files:
            if fnmatch.fnmatch(name, pattern):
                yield os.path.join(path, name)
        if not recurse:
            break


def count(root='.', recurse=True):
    """Counts lines of code in two ways:
    * maximal size (source LOC) with blank lines and comments
    * minimal size (logical LOC) stripping same

    Sums all Python files in the specified folder.
    By default recurses through subfolders.
    """
    count_mini, count_maxi = 0, 0
    for fspec in walk(root, recurse, '*.py'):
        skip = False
        with open(fspec) as f:
            for line in f:
                count_maxi += 1
                line = line.strip()
                if line:
                    if line.startswith('#'):
                        continue
                    if line.count('"""') == 1:
                        skip = not skip
                        continue
                    if not skip:
                        count_mini += 1
    return count_mini, count_maxi


if __name__ == '__main__':
    mini, maxi = count()
    print("Maximal lines: {}\nMinimal lines: {}".format(maxi, mini))
