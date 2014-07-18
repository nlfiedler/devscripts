#!/usr/bin/env python3
#
# Python script to remove the 'categories' from all Jekyll posts
# within a Jekyll blog.
#

import os
import subprocess
import sys
import tempfile

#
# Matches the multiline form of 'categories', e.g.
#
# categories:
# - foo
# - bar
#
_AWK_SCRIPT = """
/^categories:$/ {
    do {
        getline
    } while ($0 ~ /^- /)
}

{
    print $0
}
"""


def _run_awk(scriptfile, filename):
    """Process the named file, running it through our AWK script."""
    cmd = ['/usr/bin/awk', '-f', scriptfile, filename]
    output = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
    with open(filename, 'w') as fobj:
        fobj.write(output.decode())
        print("Processed {}...".format(filename))


def main():
    """Perform the work."""
    if not os.path.exists('_posts'):
        print("Please run this script in your Jekyll directory, " +
              "in which a _posts directory exists.")
        sys.exit(1)
    fh, scriptfile = tempfile.mkstemp()
    with open(fh, 'w') as fobj:
        fobj.write(_AWK_SCRIPT)
    try:
        for dirpath, _dirnames, filenames in os.walk('_posts'):
            for filename in filenames:
                _run_awk(scriptfile, os.path.join(dirpath, filename))
    finally:
        os.unlink(scriptfile)


if __name__ == "__main__":
    main()
