#!/usr/bin/env python
"""Script to automate logging into Perforce."""

import subprocess
import sys


def main():
    """Log in to the Perforce server."""
    # Yep, pretty much that easy.
    result = subprocess.check_output(['p4', 'set', '-q', 'P4PASSWD'])
    if '=' not in result:
        sys.stderr.write('Missing P4PASSWD setting!\n')
        sys.exit(2)
    passwd = result.strip().split('=')[1]
    proc = subprocess.Popen(['p4', 'login'], stdin=subprocess.PIPE)
    proc.communicate(passwd)
    sys.exit(proc.returncode)


if __name__ == "__main__":
    main()
