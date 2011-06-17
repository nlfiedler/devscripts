#!/usr/bin/python
#
# Script to replicate one filesystem to another in a repeatable fashion.
# Note that this script uses the -F option for 'zfs recv' such that the
# destination file system is rolled back before receiving the
# snapshot(s). This is necessary since otherwise the receive will fail
# due to the mismatch in existing snapshots. This occurs because simply
# listing a directory in the destination will modify the access times,
# which causes a write to the file system. The alternative is to make
# the destination read-only, but that is an extra step that which can be
# easily avoided.
#
# To test this script, create two throw-away ZFS filesystems using the
# mkfile command, as shown below:
#
# [root@solaris]$ mkfile 100m master
# [root@solaris]$ mkfile 100m slave
# [root@solaris]$ zpool create master $PWD/master
# [root@solaris]$ zpool create slave $PWD/slave
#

from datetime import datetime
import os
import re
import subprocess
import sys

def mksnapshot(fs):
    """
    Creates a snapshot for fs whose name is today's date and time in the
    following format: %Y-%m-%d-%H:%M, and returns that name. The time is
    in UTC.
    """
    # make a snapshot of the source file system with the date and time as the name
    today = datetime.utcnow()
    tag = today.strftime("%Y-%m-%d-%H:%M")
    try:
        retcode = subprocess.call(["zfs", "snapshot", "%s@%s" % (fs, tag)])
        if retcode < 0:
            print >>sys.stderr, "Child was terminated by signal", -retcode
            sys.exit(retcode)
    except OSError, e:
        print >>sys.stderr, "Execution failed:", e
        sys.exit(-1)
    return tag

def snapshots(fs):
    """
    Get the interesting snapshots for the given file system, such that
    they are named in the ISO 8601 format (i.e. YYYY-mm-dd-HH:MM).
    """
    zfs = subprocess.Popen(["zfs", "list", "-t", "snapshot", "-Hr", fs],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    # Ignore the stderr output and only read the stdout output.
    output = zfs.communicate()[0]
    snaps = output.splitlines()
    prog = re.compile("@\d{4}-\d{2}-\d{2}-\d{2}:\d{2}")
    snaps = [snap for snap in snaps if prog.search(snap)]
    snaps = [snap.split('\t')[0] for snap in snaps]
    snaps = [snap.split('@')[1] for snap in snaps]
    snaps.sort()
    return snaps

def sendsnapshot(src, dst, tag):
    """
    Send a replication stream for a single snapshot from the source
    filesystem to the destination.
    """
    send = subprocess.Popen(["zfs", "send", "-R", "%s@%s" % (src, tag)],
                            stdout=subprocess.PIPE)
    recv = subprocess.Popen(["zfs", "recv", "-F", dst], stdin=send.stdout,
                            stdout=subprocess.PIPE)
    # Allow send process to receive a SIGPIPE if recv exits early.
    send.stdout.close()
    # Read the outputs so the process finishes, but ignore them.
    recv.communicate()

def sendincremental(src, dst, tag1, tag2):
    """
    Send an incremental replication stream from the source filesystem to
    the destination that spans the two snapshots.
    """
    send = subprocess.Popen(["zfs", "send", "-R", "-I", tag1, "%s@%s" % (src, tag2)],
                            stdout=subprocess.PIPE)
    recv = subprocess.Popen(["zfs", "recv", "-F", dst], stdin=send.stdout,
                            stdout=subprocess.PIPE)
    # Allow send process to receive a SIGPIPE if recv exits early.
    send.stdout.close()
    # Read the outputs so the process finishes, but ignore them.
    recv.communicate()

def destroysnap(fs, snap):
    """
    Destroy the named snapshot in the given file system.
    """
    zfs = subprocess.Popen(["zfs", "destroy", "%s@%s" % (fs, snap)],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    # Read the outputs so the process finishes, but ignore them.
    zfs.communicate()

def main():
    if len(sys.argv) < 3:
        print "Usage: replica.py <srcfs> <dstfs>"
        sys.exit(0)

    src = sys.argv[1]
    dst = sys.argv[2]

    mksnapshot(src)
    snaps = snapshots(src)
    if snaps is None:
        print "Failed to create new snapshot in %s" % src
        sys.exit(-1)
    elif len(snaps) == 1:
        sendsnapshot(src, dst, snaps[0])
    else:
        recent = snaps[-2:]
        sendincremental(src, dst, recent[0], recent[1])

    # prune old snapshots in source file system
    oldsnaps = snaps[:-2]
    for snap in oldsnaps:
        destroysnap(src, snap)
    # prune old snapshots in destination file system
    snaps = snapshots(dst)
    if snaps is None:
        print "Failed to create new snapshot in %s" % dst
        sys.exit(-1)
    oldsnaps = snaps[:-2]
    for snap in oldsnaps:
        destroysnap(dst, snap)

if __name__ == "__main__":
    main()
