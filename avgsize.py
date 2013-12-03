#!/usr/bin/env python3
#
# Find the total size of all files in the current directory tree,
# and compute the average file size in bytes. Symbolic links are
# ignored.
#

import os
from os.path import getsize, islink, join


def count_files():
    """
    Return the number of files found and their total byte count.
    """
    total = 0
    count = 0
    for root, dirs, files in os.walk('.'):
        if '.git' in dirs:
            dirs.remove('.git')
        files = [join(root, name) for name in files]
        files = [name for name in files if not islink(name)]
        count += len(files)
        total += sum(getsize(name) for name in files)
    return (total, count)


def main():
    """
    Compute the average file size for all files in the current tree.
    """
    total, count = count_files()
    avg = total / count
    print("Total: {0}\nCount: {1}\nAverage: {2:.2f}".format(total, count, avg))


if __name__ == "__main__":
    main()
