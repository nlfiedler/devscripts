#!/usr/bin/env python3
"""Script to replicate one filesystem to another in a repeatable fashion.

Note that this script uses the -F option for 'zfs recv' such that the
destination file system is rolled back before receiving the snapshot(s).
This is necessary since otherwise the receive will fail due to the
mismatch in existing snapshots. This occurs because simply listing a
directory in the destination will modify the access times, which causes a
write to the file system. The alternative is to make the destination
read-only, but that is an extra step which can be easily avoided.

"""
#
# To test this script, create two throw-away ZFS filesystems using the
# mkfile command, as shown below:
#
# [root@solaris]$ mkfile 100m master
# [root@solaris]$ mkfile 100m slave
# [root@solaris]$ pfexec zpool create master $PWD/master
# [root@solaris]$ pfexec zpool create slave $PWD/slave
#

import argparse
from datetime import datetime
import os
import re
import subprocess
import sys

VERBOSE = False
DEBUG = False


def _call_proc(cmd):
    """Invoke the command in a subprocess and return its output.

    :param cmd: list of strings to pass to subprocess.call().

    Raises CalledProcessError if the process exit code is non-zero.

    """
    if cmd is None or not isinstance(cmd, list):
        raise RuntimeError("cmd must be a non-empty list")
    if VERBOSE:
        print(" ".join(cmd))
    output = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
    output = output.decode()
    if DEBUG:
        for line in output.splitlines():
            print("=> {}".format(line))
    return output


def _disable_auto(fsys):
    """
    Disables the auto-snapshot service for the given file system,
    returning the previous setting (true or false).
    """
    # get the previous setting for the property
    output = _call_proc(["zfs", "get", "-Ho", "value", "com.sun:auto-snapshot", fsys])
    # set the auto-snapshot property to false
    _call_proc(["zfs", "set", "com.sun:auto-snapshot=false", fsys])
    # return the previous setting
    return output.strip()


def _restore_auto(fsys, saved):
    """
    Restores the auto-snapshot property to the previously set value for
    the given file system.
    """
    # zfs get returns '-' when the property is not set.
    if saved != "-":
        _call_proc(["zfs", "set", "com.sun:auto-snapshot={}".format(saved), fsys])


def _take_snapshot(fsys):
    """
    Creates a snapshot for fsys whose name is today's date and time in the
    following format: %Y-%m-%d-%H:%M, and returns that name. The time is
    in UTC.
    """
    # make a snapshot of the source file system with the date and time
    # as the name
    today = datetime.utcnow()
    tag = today.strftime("%Y-%m-%d-%H:%M")
    _call_proc(["zfs", "snapshot", "{}@replica:{}".format(fsys, tag)])
    return tag


def _our_snapshots(fsys):
    """
    Get our mananged snapshots for the given file system, such that they
    are named "replica:" followed by a date in the ISO 8601 format (i.e.
    YYYY-mm-dd-HH:MM).
    """
    output = _call_proc(["zfs", "list", "-t", "snapshot", "-Hr", fsys])
    snaps = output.splitlines()
    prog = re.compile(r"@replica:\d{4}-\d{2}-\d{2}-\d{2}:\d{2}")
    snaps = [snap for snap in snaps if prog.search(snap)]
    snaps = [snap.split('\t')[0] for snap in snaps]
    snaps = [snap.split('@')[1] for snap in snaps]
    snaps.sort()
    if DEBUG:
        print("Existing snapshots on {}...".format(fsys))
        for snap in snaps:
            print(snap)
    return snaps


def _send_snapshot(src, dst, tag):
    """
    Send a replication stream for a single snapshot from the source
    filesystem to the destination.
    """
    if VERBOSE:
        print("zfs send -R {}@{} | zfs recv -F {}".format(src, tag, dst))
    send = subprocess.Popen(["zfs", "send", "-R", "{}@{}".format(src, tag)],
                            stdout=subprocess.PIPE)
    recv = subprocess.Popen(["zfs", "recv", "-F", dst], stdin=send.stdout,
                            stdout=subprocess.PIPE)
    # Allow send process to receive a SIGPIPE if recv exits early.
    send.stdout.close()
    # Read the outputs so the process finishes, but ignore them.
    recv.communicate()
    if send.returncode != 0 and send.returncode is not None:
        raise subprocess.CalledProcessError(send.returncode, "zfs send")
    if recv.returncode != 0 and recv.returncode is not None:
        raise subprocess.CalledProcessError(recv.returncode, "zfs recv")


def _send_incremental(src, dst, tag1, tag2):
    """
    Send an incremental replication stream from the source filesystem to
    the destination that spans the two snapshots.
    """
    if VERBOSE:
        print("zfs send -R -I {} {}@{} | zfs recv -F {}".format(tag1, src, tag2, dst))
    send = subprocess.Popen(["zfs", "send", "-R", "-I", tag1, "{}@{}".format(src, tag2)],
                            stdout=subprocess.PIPE)
    recv = subprocess.Popen(["zfs", "recv", "-F", dst], stdin=send.stdout,
                            stdout=subprocess.PIPE)
    # Allow send process to receive a SIGPIPE if recv exits early.
    send.stdout.close()
    # Read the outputs so the process finishes, but ignore them.
    recv.communicate()
    if send.returncode != 0 and send.returncode is not None:
        raise subprocess.CalledProcessError(send.returncode, "zfs send")
    if recv.returncode != 0 and recv.returncode is not None:
        raise subprocess.CalledProcessError(recv.returncode, "zfs recv")


def _destroy_snapshot(fsys, snap):
    """
    Destroy the named snapshot in the given file system.
    """
    output = _call_proc(["zfs", "destroy", "{}@{}".format(fsys, snap)])
    if DEBUG:
        print(output)


def _create_and_send_snapshot(src, dst):
    """Create a snapshot and send it to the destination.

    :param src: source file system
    :param dst: destination file system

    """
    # make the new snapshot, get a list of existing snapshots,
    # and decide whether to send a full stream or an incremental
    _take_snapshot(src)
    snaps = _our_snapshots(src)
    if snaps is None or len(snaps) == 0:
        raise OSError("Failed to create new snapshot in {}".format(src))
    dstsnaps = _our_snapshots(dst)
    if dstsnaps is not None and len(dstsnaps) > 0 \
            and dstsnaps[-1] not in snaps:
        raise OSError("Destination snapshots out of sync with source, destroy and try again.")
    if len(snaps) == 1:
        # send the initial snapshot
        _send_snapshot(src, dst, snaps[0])
    elif dstsnaps is None or len(dstsnaps) == 0:
        # send the latest snapshot since the destination has none
        _send_snapshot(src, dst, snaps[-1])
    else:
        # destination has matching snapshots, send an incremental
        recent = snaps[-2:]
        _send_incremental(src, dst, recent[0], recent[1])


def _prune_old_snapshots(src, dst):
    """Prune the old replica snapshots from source and destination.

    :param src: source file system
    :param dst: destination file system

    """
    # prune old snapshots in source file system
    snaps = _our_snapshots(src)
    oldsnaps = snaps[:-2]
    for snap in oldsnaps:
        _destroy_snapshot(src, snap)
    # prune old snapshots in destination file system
    dstsnaps = _our_snapshots(dst)
    if dstsnaps is None or len(dstsnaps) == 0:
        raise OSError("Failed to create new snapshot in {}".format(dst))
    oldsnaps = dstsnaps[:-2]
    for snap in oldsnaps:
        _destroy_snapshot(dst, snap)


def main():
    """Do the work."""
    desc = """This script creates a snapshot on the source ZFS file system and sends
that in the form of a replication stream to the destination file system.
If a previous snapshot created by this script exists then this script
will create a new snapshot and send an incremental replication stream to
the destination. Older snapshots on both the source and destination will
be automatically pruned such that the two most recent are retained."""
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument('src', help='Source ZFS file system')
    parser.add_argument('dest', help='Destination ZFS file system')
    args = parser.parse_args()
    src = args.src
    dst = args.dest

    # disable the auto-snapshot service to prevent spurious failures
    try:
        assrc = _disable_auto(src)
        asdst = _disable_auto(dst)
    except subprocess.CalledProcessError as cpe:
        print("Unable to acquire/modify auto-snapshot status.", file=sys.stderr)
        if cpe.output:
            sys.stderr.write(cpe.output.decode())
        sys.exit(cpe.returncode)
    try:
        _create_and_send_snapshot(src, dst)
        _prune_old_snapshots(src, dst)
    except subprocess.CalledProcessError as cpe:
        if cpe.output:
            sys.stderr.write(cpe.output.decode())
        sys.exit(cpe.returncode)
    except OSError as ose:
        sys.stderr.write(str(ose))
        sys.exit(os.EX_OSERR)
    finally:
        # restore the auto-snapshot property on the file systems
        _restore_auto(dst, asdst)
        _restore_auto(src, assrc)


if __name__ == "__main__":
    main()
