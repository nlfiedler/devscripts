#!/usr/bin/env python3
#
# Script to replicate one filesystem to another in a repeatable fashion. Note
# that this script uses the -F option for 'zfs recv' such that the destination
# file system is rolled back before receiving the snapshot(s). This is
# necessary since otherwise the receive will fail due to the mismatch in
# existing snapshots. This occurs because simply listing a directory in the
# destination will modify the access times, which causes a write to the file
# system. The alternative is to make the destination read-only, but that is an
# extra step which can be easily avoided.
#
# To test this script, create two throw-away ZFS filesystems using the mkfile
# command, as shown below:
#
# [root@solaris]$ mkfile 100m master
# [root@solaris]$ mkfile 100m slave
# [root@solaris]$ zpool create master $PWD/master
# [root@solaris]$ zpool create slave $PWD/slave
#

from datetime import datetime
import errno
import getopt
import re
import subprocess
import sys

verbose = False
debug = False


def disableauto(fs):
    """
    Disables the auto-snapshot service for the given file system,
    returning the previous setting (true or false).
    """
    # get the previous setting for the property
    if verbose:
        print("zfs get -Ho value com.sun:auto-snapshot {}".format(fs))
    zfs = subprocess.Popen(["zfs", "get", "-Ho", "value",
                            "com.sun:auto-snapshot", fs],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output = zfs.communicate()[0]
    if zfs.returncode != 0:
        raise OSError(errno.EIO, "zfs get returned {}".format(zfs.returncode))
    # set the auto-snapshot property to false
    try:
        if verbose:
            print("zfs set com.sun:auto-snapshot=false {}".format(fs))
        retcode = subprocess.call(["zfs", "set",
                                   "com.sun:auto-snapshot=false", fs])
        if retcode < 0:
            print("Child was terminated by signal {}".format(-retcode), file=sys.stderr)
            sys.exit(retcode)
    except OSError as e:
        print("Execution failed:", e, file=sys.stderr)
        sys.exit(1)
    # return the previous setting
    return output


def restoreauto(fs, saved):
    """
    Restores the auto-snapshot property to the previously set value for
    the given file system.
    """
    try:
        if verbose:
            print("zfs set com.sun:auto-snapshot={} {}".format(saved, fs))
        retcode = subprocess.call(["zfs", "set", "com.sun:auto-snapshot={}".
                                   format(saved), fs])
        if retcode < 0:
            print("Child was terminated by signal", -retcode, file=sys.stderr)
            sys.exit(retcode)
    except OSError as e:
        print("Execution failed:", e, file=sys.stderr)
        sys.exit(1)


def mksnapshot(fs):
    """
    Creates a snapshot for fs whose name is today's date and time in the
    following format: %Y-%m-%d-%H:%M, and returns that name. The time is
    in UTC.
    """
    # make a snapshot of the source file system with the date and time
    # as the name
    today = datetime.utcnow()
    tag = today.strftime("%Y-%m-%d-%H:%M")
    try:
        if verbose:
            print("zfs snapshot {}@replica:{}".format(fs, tag))
        retcode = subprocess.call(["zfs", "snapshot",
                                   "{}@replica:{}".format(fs, tag)])
        if retcode < 0:
            print("Child was terminated by signal", -retcode, file=sys.stderr)
            sys.exit(retcode)
    except OSError as e:
        print("Execution failed:", e, file=sys.stderr)
        sys.exit(1)
    return tag


def snapshots(fs):
    """
    Get our mananged snapshots for the given file system, such that they
    are named "replica:" followed by a date in the ISO 8601 format (i.e.
    YYYY-mm-dd-HH:MM).
    """
    if verbose:
        print("zfs list -t snapshot -Hr {}".format(fs))
    zfs = subprocess.Popen(["zfs", "list", "-t", "snapshot", "-Hr", fs],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    # Ignore the stderr output and only read the stdout output.
    output = zfs.communicate()[0]
    if zfs.returncode != 0:
        raise OSError(errno.EIO, "zfs list returned {}".format(zfs.returncode))
    if isinstance(output, bytes):
        output = output.decode('utf-8')
    snaps = output.splitlines()
    prog = re.compile("@replica:\d{4}-\d{2}-\d{2}-\d{2}:\d{2}")
    snaps = [snap for snap in snaps if prog.search(snap)]
    snaps = [snap.split('\t')[0] for snap in snaps]
    snaps = [snap.split('@')[1] for snap in snaps]
    snaps.sort()
    if debug:
        print("Existing snapshots on {}...".format(fs))
        for snap in snaps:
            print(snap)
    return snaps


def sendsnapshot(src, dst, tag):
    """
    Send a replication stream for a single snapshot from the source
    filesystem to the destination.
    """
    if verbose:
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
        raise OSError(errno.EIO, "zfs send returned {}".
                      format(send.returncode))
    if recv.returncode != 0 and send.returncode is not None:
        raise OSError(errno.EIO, "zfs recv returned {}".
                      format(recv.returncode))


def sendincremental(src, dst, tag1, tag2):
    """
    Send an incremental replication stream from the source filesystem to
    the destination that spans the two snapshots.
    """
    if verbose:
        print("zfs send -R -I {} {}@{} | zfs recv -F {}".format(
            tag1, src, tag2, dst))
    send = subprocess.Popen(["zfs", "send", "-R", "-I", tag1, "{}@{}".format(src, tag2)],
                            stdout=subprocess.PIPE)
    recv = subprocess.Popen(["zfs", "recv", "-F", dst], stdin=send.stdout,
                            stdout=subprocess.PIPE)
    # Allow send process to receive a SIGPIPE if recv exits early.
    send.stdout.close()
    # Read the outputs so the process finishes, but ignore them.
    recv.communicate()
    if send.returncode != 0 and send.returncode is not None:
        raise OSError(errno.EIO, "zfs send returned {}".
                      format(send.returncode))
    if recv.returncode != 0 and send.returncode is not None:
        raise OSError(errno.EIO, "zfs recv returned {}".
                      format(recv.returncode))


def destroysnap(fs, snap):
    """
    Destroy the named snapshot in the given file system.
    """
    if verbose:
        print("zfs destroy {}@{}".format(fs, snap))
    zfs = subprocess.Popen(["zfs", "destroy", "{}@{}".format(fs, snap)],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    # Read the outputs so the process finishes, but ignore them.
    zfs.communicate()
    if zfs.returncode != 0:
        raise OSError(errno.EIO, "zfs destroy returned {}".
                      format(zfs.returncode))


def main():
    # parse the command line arguments
    shortopts = "h"
    longopts = ["help"]
    # keep using getopt until Python 2.7 is available on OpenIndiana,
    # then we can switch to using argparse
    try:
        opts, args = getopt.getopt(sys.argv[1:], shortopts, longopts)
    except getopt.GetoptError as err:
        print(str(err))
        print("Invoke with -h for help.")
        sys.exit(2)
    for opt, val in opts:
        if opt in ("-h", "--help"):
            usage()
            sys.exit()
        else:
            assert False, "unhandled option: {}".format(opt)

    if len(args) < 2:
        print("Usage: replica.py [options] <srcfs> <dstfs>")
        print("Invoke with --help for helpful information")
        sys.exit(0)

    src = args[0]
    dst = args[1]

    try:
        # disable the auto-snapshot service to prevent spurious failures
        assrc = disableauto(src)
        asdst = disableauto(dst)
        # make the new snapshot, get a list of existing snapshots,
        # and decide whether to send a full stream or an incremental
        mksnapshot(src)
        snaps = snapshots(src)
        if snaps is None or len(snaps) == 0:
            print("Failed to create new snapshot in {}".format(src))
            sys.exit(1)
        dstsnaps = snapshots(dst)
        if dstsnaps is not None and len(dstsnaps) > 0 \
                and dstsnaps[-1] not in snaps:
            print("Destination snapshots out of sync with source, destroy and try again.")
            sys.exit(1)
        if len(snaps) == 1:
            # send the initial snapshot
            sendsnapshot(src, dst, snaps[0])
        elif dstsnaps is None or len(dstsnaps) == 0:
            # send the latest snapshot since the destination has none
            sendsnapshot(src, dst, snaps[-1])
        else:
            # destination has matching snapshots, send an incremental
            recent = snaps[-2:]
            sendincremental(src, dst, recent[0], recent[1])

        # prune old snapshots in source file system
        oldsnaps = snaps[:-2]
        for snap in oldsnaps:
            destroysnap(src, snap)
        # prune old snapshots in destination file system
        dstsnaps = snapshots(dst)
        if dstsnaps is None or len(dstsnaps) == 0:
            print("Failed to create new snapshot in {}".format(dst))
            sys.exit(1)
        oldsnaps = dstsnaps[:-2]
        for snap in oldsnaps:
            destroysnap(dst, snap)
        # restore the auto-snapshot property on the file systems
        restoreauto(dst, asdst)
        restoreauto(src, assrc)
    except OSError as e:
        print("Execution failed:", e, file=sys.stderr)
        sys.exit(1)


def usage():
    print("""Usage: replica.py [-h] <srcfs> <dstfs>

This script creates a snapshot on the source ZFS file system and sends
that in the form of a replication stream to the destination file system.
If a previous snapshot created by this script exists then this script
will create a new snapshot and send an incremental replication stream to
the destination. Older snapshots on both the source and destination will
be automatically pruned such that the two most recent are retained.

-h|--help
\tPrints this usage information.
""")

if __name__ == "__main__":
    main()
