#!/usr/bin/env python3
"""Finds and updates the Git repositories.

This is a highly specialized script that assumes that the repositories
in question are bare (i.e. no working tree) and have a single remote.

To create the initial backup repositories, clone them like so:

$ git clone --mirror <git_url>

Requirements
* python-sh (pip install sh)

"""

import os
import stat
import sys

from sh import git


def _get_directories(path):
    """Generate a list of directoires in the given path.

    :param path: path to be visited.

    Yields each directory within path one by one.

    """
    for entry in os.listdir(path):
        pathname = os.path.join(path, entry)
        mode = os.lstat(pathname)[stat.ST_MODE]
        if stat.S_ISDIR(mode):
            yield pathname


def _git_remote(path):
    """Return the (fetch) URL for the remote repository.

    :param path: path of the local Git repository.

    """
    output = git("--git-dir={}".format(path), "remote").splitlines()
    if len(output) > 1:
        sys.stderr.write('Too much output from `git remote` for {}'.format(path))
        sys.exit(os.EX_OSERR)
    remote = output[0]
    output = git("--git-dir={}".format(path), "remote", "-v").splitlines()
    fetch_url = None
    for line in output:
        if line.startswith(remote) and line.endswith(' (fetch)'):
            _, fetch_url, _ = line.split()
            break
    return remote, fetch_url


def main():
    """Do the work."""
    ignored_list = []
    for candidate in sorted(_get_directories('.')):
        if os.path.exists(os.path.join(candidate, 'HEAD')):
            remote, fetch_url = _git_remote(candidate)
            git("--git-dir={}".format(candidate), "fetch", remote)
            print('Fetched {} successfully for {}'.format(fetch_url, candidate))
        else:
            ignored_list.append(candidate)
    for ignored in ignored_list:
        print("Ignored non-Git entry {}".format(ignored))


if __name__ == "__main__":
    main()
