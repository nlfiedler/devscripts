#!/usr/bin/env python3
"""Fix permissions of files and directories."""

import argparse
import os
import stat
import sys


def _fix_perms(leading, names, perms):
    """Fix permissions of a set of entities.

    :param leading: the leading path to the entities.
    :param names: list of file/dir entities to fix.
    :param perms: desired permissions.

    """
    for name in names:
        path = os.path.join(leading, name)
        if stat.S_IMODE(os.stat(path).st_mode) != perms:
            os.chmod(path, perms)


def main():
    """Fix permissions of files and directories."""
    parser = argparse.ArgumentParser(description="Fix permissions of files and directories.")
    parser.add_argument('-f', '--file', default='644',
                        help="permissions for files (default 644)")
    parser.add_argument('-d', '--dir', default='755',
                        help="permissions for directories (default 755)")
    parser.add_argument('-x', '--exclude', nargs="*",
                        help="entries to ignore (can specify more than one)")
    parser.add_argument('-p', '--path', nargs="*", default=".",
                        help="one or more paths to process (default .)")
    args = parser.parse_args()
    fperms = int(args.file, 8)
    dperms = int(args.dir, 8)
    if fperms > 0o777 or fperms < 0o400:
        print('Invalid file permissions: {}'.format(args.file))
        sys.exit(1)
    if dperms > 0o777 or dperms < 0o400:
        print('Invalid directory permissions: {}'.format(args.dir))
        sys.exit(1)
    for path in args.path:
        for dirpath, dirnames, filenames in os.walk(path):
            if args.exclude:
                for ii in range(len(dirnames) - 1, 0, -1):
                    if dirnames[ii] in args.exclude:
                        dirnames.pop(ii)
                for ii in range(len(filenames) - 1, 0, -1):
                    if filenames[ii] in args.exclude:
                        filenames.pop(ii)
            _fix_perms(dirpath, filenames, fperms)
            _fix_perms(dirpath, dirnames, dperms)


if __name__ == "__main__":
    main()
