#!/usr/bin/env python3
"""Script to automate logging into Perforce."""

import subprocess
import sys


def main():
    """Log in to the Perforce server."""
    # Yep, pretty much that easy.
    result = subprocess.check_output(['p4', 'set', '-q', 'P4PASSWD'], text=True)
    if '=' not in result:
        sys.stderr.write('Missing P4PASSWD setting!\n')
        sys.exit(2)
    passwd = result.strip().split('=')[1]
    proc = subprocess.Popen(['p4', 'login'], stdin=subprocess.PIPE, text=True)
    proc.communicate(passwd)
    sys.exit(proc.returncode)


if __name__ == "__main__":
    main()
