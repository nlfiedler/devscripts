#!/usr/bin/env python3
"""Script to replicate one ZFS filesystem to another in a repeatable fashion.

Note that this script uses the -F option for 'zfs recv' such that the
destination file system is rolled back before receiving the snapshot(s).
This is necessary since otherwise the receive will fail due to the mismatch
in existing snapshots. This occurs because simply listing a directory in
the destination will modify the access times, which causes a write to the
file system. The alternative is to make the destination read-only, but that
is an extra step which can be easily avoided.

Requirements:
* python-sh (pip install sh)

"""
#
# To test this script, create two throw-away ZFS filesystems, where "tank"
# is the name of the pool in which the file systems will be created:
#
# $ sudo zfs create tank/source
# $ sudo zfs create tank/target
#

import argparse
from datetime import datetime
import logging
import os
import re
import subprocess
import sys

from sh import zfs

LOG = logging.getLogger('replica')
DEFAULT_LOG_FORMAT = '[%(process)d] <%(asctime)s> (%(name)s) {%(levelname)s} %(message)s'
DEFAULT_LOG_FILE = '/var/log/replica.log'


def _configure_logging():
    """Configure the logging system."""
    LOG.setLevel(logging.INFO)
    handler = logging.FileHandler(DEFAULT_LOG_FILE)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter(DEFAULT_LOG_FORMAT)
    handler.setFormatter(formatter)
    LOG.addHandler(handler)


def _disable_auto(fsys):
    """Disable the auto-snapshot service for the given file system.

    :param fsys: file system on which to set property.
    :return: previous value for auto-snapshot propery.

    """
    output = zfs.get("-Ho", "value", "com.sun:auto-snapshot", fsys)
    zfs.set("com.sun:auto-snapshot=false", fsys)
    LOG.info('disabled auto-snapshot on {}'.format(fsys))
    return output.strip()


def _restore_auto(fsys, saved):
    """Restore the auto-snapshot property to the previously set value.

    :param fsys: file system on which to set property.
    :param saved: previous value of auto-snapshot property

    """
    # zfs get returns '-' when the property is not set.
    if saved != "-":
        zfs.set("com.sun:auto-snapshot={}".format(saved), fsys)
        LOG.info('set auto-snapshot to {} on {}'.format(saved, fsys))


def _take_snapshot(fsys):
    """Create a snapshot on the named file system.

    Creates a snapshot for fsys whose name is today's date and time in the
    following format: %Y-%m-%d-%H:%M, and returns that name. The time is
    in UTC.

    :param fsys: file system on which to create snapshot.
    :return: name of snapshot that was created.

    """
    # make a snapshot of the source file system with the date and time
    # as the name
    today = datetime.utcnow()
    tag = today.strftime("%Y-%m-%d-%H:%M")
    snap_name = "{}@replica:{}".format(fsys, tag)
    zfs.snapshot(snap_name)
    LOG.info('created snapshot {}'.format(snap_name))
    return tag


def _our_snapshots(fsys):
    """Return a list of the snapshots created by this script.

    Get our mananged snapshots for the given file system, such that they
    are named "replica:" followed by a date in the ISO 8601 format (i.e.
    YYYY-mm-dd-HH:MM).

    :param fsys: file system on which to find snapshots.
    :return: list of snapshot names.

    """
    LOG.info('fetching snapshots')
    output = zfs.list("-t", "snapshot", "-Hr", fsys)
    snaps = output.splitlines()
    prog = re.compile(r"@replica:\d{4}-\d{2}-\d{2}-\d{2}:\d{2}")
    snaps = [snap for snap in snaps if prog.search(snap)]
    snaps = [snap.split('\t')[0] for snap in snaps]
    snaps = [snap.split('@')[1] for snap in snaps]
    snaps.sort()
    return snaps


def _send_snapshot(src, dst, tag):
    """Send a replication stream for a single snapshot.

    :param src: source file system
    :param dst: destination file system
    :param tag: snapshot to be sent

    """
    LOG.info('sending full snapshot from {} to {}'.format(src, dst))
    send = subprocess.Popen(["zfs", "send", "-R", "{}@{}".format(src, tag)],
                            stdout=subprocess.PIPE)
    recv = subprocess.Popen(["zfs", "recv", "-F", dst], stdin=send.stdout,
                            stdout=subprocess.PIPE)
    # Allow send process to receive a SIGPIPE if recv exits early.
    send.stdout.close()
    # Read the outputs so the process finishes, but ignore them.
    recv.communicate()
    LOG.info('full snapshot sent')
    if send.returncode != 0 and send.returncode is not None:
        raise subprocess.CalledProcessError(send.returncode, "zfs send")
    if recv.returncode != 0 and recv.returncode is not None:
        raise subprocess.CalledProcessError(recv.returncode, "zfs recv")


def _send_incremental(src, dst, tag1, tag2):
    """Send an incremental replication stream from source to target.

    :param src: source file system
    :param dst: destination file system
    :param tag1: starting snapshot
    :param tag2: ending snapshot

    """
    LOG.info('sending incremental snapshot from {} to {}'.format(src, dst))
    # Tried this with python-sh but recv failed to read from send
    # zfs.recv(zfs.send("-R", "-I", tag1, "{}@{}".format(src, tag2), _piped=True), "-F", dst)
    send = subprocess.Popen(["zfs", "send", "-R", "-I", tag1, "{}@{}".format(src, tag2)],
                            stdout=subprocess.PIPE)
    recv = subprocess.Popen(["zfs", "recv", "-F", dst], stdin=send.stdout,
                            stdout=subprocess.PIPE)
    # Allow send process to receive a SIGPIPE if recv exits early.
    send.stdout.close()
    # Read the outputs so the process finishes, but ignore them.
    recv.communicate()
    LOG.info('incremental snapshot sent')
    if send.returncode != 0 and send.returncode is not None:
        raise subprocess.CalledProcessError(send.returncode, "zfs send")
    if recv.returncode != 0 and recv.returncode is not None:
        raise subprocess.CalledProcessError(recv.returncode, "zfs recv")


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
        zfs.destroy("{}@{}".format(src, snap))
        LOG.info('deleted old snapshot {}'.format(snap))
    # prune old snapshots in destination file system
    dstsnaps = _our_snapshots(dst)
    if dstsnaps is None or len(dstsnaps) == 0:
        raise OSError("Failed to create new snapshot in {}".format(dst))
    oldsnaps = dstsnaps[:-2]
    for snap in oldsnaps:
        zfs.destroy("{}@{}".format(dst, snap))
        LOG.info('deleted old snapshot {}'.format(snap))


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

    _configure_logging()

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
