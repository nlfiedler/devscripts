#!/usr/bin/env python3
#
# Python script to create tarballs of selected directories and upload to
# Amazon Glacier. Archives older than three months are pruned.
#
# Reads settings from a configuration file, using whichever of the
# following is found first (in this order):
#
# 1. ./.glacier.conf
# 2. ~/.glacier.conf
# 3. /etc/glacier.conf
#
# Requires ZFS (i.e. 'zfs' command is in the PATH) to create snapshots
# and clones of filesystems prior to creating archives.
#
# Requires https://github.com/uskudnik/amazon-glacier-cmd-interface to
# be installed and 'glacier-cmd' to be in the PATH.
#

import argparse
import configparser
from contextlib import contextmanager
from datetime import datetime, timedelta
import os
import re
import subprocess
import sys
import tarfile
import time

verbose = False


def _read_config():
    """
    Find a configuration file, looking first in the current directory, and
    then looking in the user's home directory. Returns the initialized
    instance of ConfigParser. Exits if configuration file is missing.
    """
    cfg_name = '.glacier.conf'
    if not os.path.exists(cfg_name):
        cfg_name = os.path.expanduser("~/.glacier.conf")
        if not os.path.exists(cfg_name):
            cfg_name = "/etc/glacier.conf"
            if not os.path.exists(cfg_name):
                sys.stderr.write("Missing .glacier.conf file!")
                sys.exit(1)
    if verbose:
        print("Reading configuration file {}".format(cfg_name))
    config = configparser.ConfigParser()
    config.read(cfg_name)
    return config


def _get_config(parser, section, option):
    """
    Retrieve the named configuration option. Exits if option is missing.
    """
    if not parser.has_section(section):
        fmt = "Missing section {} in configuration file!\n"
        sys.stderr.write(fmt.format(section))
        sys.exit(1)
    value = parser.get(section, option, fallback=None)
    if value is None:
        fmt = "Missing option {}/{} in configuration file!\n"
        sys.stderr.write(fmt.format(section, option))
        sys.exit(1)
    return value


def _run_cmd(cmd, call=False):
    """
    Run the given command, returning its output. If the process exits
    with a non-zero status, an error is displayed and this process dies.

    Arguments:
        call -- if True, direct stdout/stderr to sys.stdout and sys.stderr;
                returns an empty bytes object
    """
    assert isinstance(cmd, list), 'cmd must be a list'
    if verbose:
        print(" ".join(cmd))
    try:
        if call:
            retcode = subprocess.call(cmd, stdout=sys.stdout,
                                      stderr=sys.stderr)
            (out, err) = (b'', b'')
        else:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
            (out, err) = proc.communicate()
            retcode = proc.returncode
    except OSError as e:
        sys.stderr.write("{} execution failed: {}\n".format(cmd, e))
        sys.exit(os.EX_OSERR)
    if retcode != 0:
        sys.stderr.write("{} failed with signal {}\n".format(cmd, retcode))
        sys.stderr.write(err.decode())
        sys.exit(retcode)
    if verbose and out:
        print(out)
    return out.decode()


@contextmanager
def pop_chdir(path):
    """
    Context manager to temporarily change to the given directory.
    """
    cwd = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(cwd)


def _dataset_exists(name):
    """
    Determine if the named ZFS dataset exists or not.
    """
    try:
        proc = subprocess.Popen(['zfs', 'list', '-H', name],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        proc.communicate()
    except OSError as e:
        sys.stderr.write("zfs list execution failed: {}\n".format(e))
        sys.exit(os.EX_OSERR)
    return proc.returncode == 0


def _path_exists(name, path, create=False):
    """
    Check that the path exists, exiting with an error if not.
    """
    if not os.path.exists(path):
        if not create:
            sys.stderr.write("{} ('{}') is missing!\n".format(name, path))
            sys.exit(1)
        try:
            os.makedirs(path)
        except OSError as e:
            sys.stderr.write("{}\n".format(e))
            sys.exit(1)


def _ensure_snapshot_exists(snapshot):
    """
    Create the ZFS snapshot, if it is missing.
    """
    if not _dataset_exists(snapshot):
        _run_cmd(["zfs", "snapshot", snapshot])


def _ensure_clone_exists(clone, snapshot):
    """
    Create the ZFS clone, if it is missing.
    """
    if not _dataset_exists(clone):
        _run_cmd(["zfs", "clone", "-p", snapshot, clone])


def _ensure_vault_exists(name):
    """
    Check if the named vault exists or not.
    Returns True if vault already exists, False if created.
    """
    lsvault = _run_cmd(["glacier-cmd", "lsvault"])
    if name not in lsvault:
        _run_cmd(["glacier-cmd", "mkvault", name])
        return False
    return True


def _prune_vaults():
    """
    Remove any vaults older than three months.
    """
    lsvault = _run_cmd(["glacier-cmd", "lsvault"])
    regex = re.compile('\d{4}-\d{2}-\d{2}T\d{2}:\d{2}')
    old = datetime.utcnow() - timedelta(100)
    for line in lsvault.splitlines():
        m = regex.search(line)
        if m is None:
            continue
        dt = datetime.strptime(m.group(0), "%Y-%m-%dT%H:%M")
        if dt < old:
            vault = line.split('|')[-1].strip()
            _run_cmd(["glacier-cmd", "rmvault", vault])


def _retrieve_inventory(vault):
    """
    Retrieves the archive descriptions of each entry in the named vault.
    """
    i = _run_cmd(['glacier-cmd', 'inventory', vault])
    return [l.split('|')[1] for l in i.splitlines() if l[0] == '|']


def _backup_single(vault, label, tmpdir, paths, archives):
    """
    For each path entry, create a compressed tar and upload to the named
    vault, then remove the tar file.

    Arguments:
        vault -- name of Glacier vault to receive archive
        label -- basename for the archive
        tmpdir -- where archive will be assembled
        paths -- files/directories to be added to archive
        archives -- list of archives already in vault
    """
    start_time = time.time()
    with pop_chdir(tmpdir):
        tarball = "{}.tar.bz2".format(label)
        if tarball not in archives:
            if not os.path.exists(tarball):
                if verbose:
                    print("Creating tarball {}...".format(tarball))
                with tarfile.open(tarball, "w:bz2") as tar:
                    for name in paths:
                        if verbose:
                            print("...adding {}...".format(name))
                        tar.add(name)
            desc = "--description '{}'".format(tarball)
            # TODO: find out if boto has timeout/retry config settings
            #       (fork boto to add these, if necessary)
            #       (or fork amazon-glacier-cmd-interface to add timeout handling)
            _run_cmd(["glacier-cmd", "upload", vault, tarball, desc], True)
            os.unlink(tarball)
    elapsed = (start_time - time.time()) / 60
    print("Archive {} processed in {} minutes".format(label, elapsed))


def main():
    """
    Read the configuration file and perform the backup procedure.
    """
    desc = """Copy directories within a ZFS clone to Amazon Glacier."""
    parser = argparse.ArgumentParser(description=desc)
    v_help = 'print actions to the console as they are performed'
    parser.add_argument('-v', '--verbose', action='store_true', help=v_help)
    l_help = "label for ZFS snapshot and Glacier vault, e.g. today's date"
    parser.add_argument('LABEL', help=l_help)
    args = parser.parse_args()
    global verbose
    if args.verbose:
        verbose = True

    # TODO: invoke this script via cron with `date -u +'%F'` as LABEL

    config = _read_config()
    tmpdir = _get_config(config, 'paths', 'tmpdir')
    _path_exists('tmpdir', tmpdir, True)
    is_vault = lambda n: n.startswith('vault_')
    sections = [n for n in config.sections() if is_vault(n)]
    for section in sections:
        root = _get_config(config, section, 'root')
        _path_exists('root', root)
        snapshot = "{}@glacier:{}".format(root[1:], args.label)
        _ensure_snapshot_exists(snapshot)
        clone_base = _get_config(config, section, 'clone_base')
        clone = os.path.join(clone_base, os.path.basename(root))
        _ensure_clone_exists(clone, snapshot)
        vault = "{}-{}".format(section[6:], args.label)
        archives = []
        if not _ensure_vault_exists(vault):
            archives = _retrieve_inventory(vault)
        is_archive = lambda n: n.startswith('archive_')
        options = [n for n in config.options(section) if is_archive(n)]
        for option in options:
            paths = [p.strip() for p in config[section][option].split(',')]
            paths = [os.path.join(root, p) for p in paths]
            _backup_single(vault, option[8:], tmpdir, paths, archives)
        _run_cmd(["zfs", "destroy", clone])
        _run_cmd(["zfs", "destroy", snapshot])
    _prune_vaults()


if __name__ == "__main__":
    main()
