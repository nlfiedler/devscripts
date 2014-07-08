#!/usr/bin/env python3
"""Script to automate logging into Perforce.

Use P4API to log in to the server.

"""

import P4


def main():
    """Log in to the Perforce server."""
    # Yep, pretty much that easy.
    p4 = P4.P4()
    p4.connect()
    p4.run_login()


if __name__ == "__main__":
    main()
