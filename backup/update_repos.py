#!/usr/bin/env python3
"""Finds and updates the Git repositories.

This is a highly specialized script that assumes that the repositories
in question are bare (i.e. no working tree) and have a single remote.

To create the initial backup repositories, clone them like so:

$ git clone --mirror <git_url>

"""

import os
import stat
import subprocess
import sys


def _call_git(gitdir, cmd):
    """Invoke git with the given command and git-dir path.

    Returns the output from the command decoded as a list of strings.

    :param gitdir: path to the Git repository's .git directory.
    :param cmd: (list) command and arguments to invoke.

    If an error occurs, this script will exit.

    """
    if cmd is None or not isinstance(cmd, list):
        raise RuntimeError('cmd must be a non-empty list')
    if cmd[0] == 'git':
        cmd = cmd[1:]
    try:
        out = subprocess.check_output(['git', '--git-dir={}'.format(gitdir)] + cmd,
                                      stderr=subprocess.STDOUT)
        return out.decode().splitlines()
    except subprocess.CalledProcessError as cpe:
        sys.stderr.write('`{}` failed with code {}\n{}\n'.format(
            cpe.cmd, cpe.returncode, cpe.output))
        sys.exit(os.EX_OSERR)


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
    output = _call_git(path, ['remote'])
    if len(output) > 1:
        sys.stderr.write('Too much output from `git remote` for {}'.format(path))
        sys.exit(os.EX_OSERR)
    remote = output[0]
    output = _call_git(path, ['remote', '-v'])
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
            _call_git(candidate, ['fetch', remote])
            print('Fetched {} successfully for {}'.format(fetch_url, candidate))
        else:
            ignored_list.append(candidate)
    for ignored in ignored_list:
        print("Ignored non-Git entry {}".format(ignored))


if __name__ == "__main__":
    main()
