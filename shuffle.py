#!/usr/bin/env python3
#
# Python script to shuffle the lines of a text file.
#

import os.path
import random
import sys


def main():
    if len(sys.argv) == 1:
        print("Usage: %s <inputfile>" % os.path.basename(sys.argv[0]))
        exit(1)
    with open(sys.argv[1]) as f:
            lines = f.readlines()
    random.shuffle(lines)
    for line in lines:
        print(line, end=' ')  # suppress trailing newline

if __name__ == "__main__":
    main()
