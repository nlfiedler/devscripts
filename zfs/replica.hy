#!/usr/bin/env hy
;
; Script to replicate one ZFS filesystem to another in a repeatable fashion.
;
; This script creates a snapshot on the source ZFS file system and sends that in
; the form of a replication stream to the destination file system. If a previous
; snapshot created by this script exists then this script will create a new
; snapshot and send an incremental replication stream to the destination. Older
; snapshots on both the source and destination will be automatically pruned such
; that the two most recent are retained.
;
; Note that this script uses the -F option for 'zfs recv' such that the
; destination file system is rolled back before receiving the snapshot(s). This
; is necessary since otherwise the receive will fail due to the mismatch in
; existing snapshots. This occurs because simply listing a directory in the
; destination will modify the access times, which causes a write to the file
; system. The alternative is to make the destination read-only, but that is an
; extra step which can be easily avoided.
;
; To test this script, create two throw-away ZFS filesystems, where "tank" is
; the name of the pool in which the file systems will be created:
;
; $ sudo zfs create tank/source
; $ sudo zfs create tank/target
;
; Requirements:
; * python-sh (pip install sh)
;

(import argparse)
(import [datetime [datetime]])
(import logging)
(import os)
(import re)
(import subprocess)
(import sys)

(import [sh [zfs]])

(setv *log* (logging.getLogger "replica"))
(setv *default-log-format* "[%(process)d] <%(asctime)s> (%(name)s) {%(levelname)s} %(message)s")
(setv *default-log-file* "/var/log/replica.log")

(defn configure-logging []
  ;
  ; Configure the logging system.
  ;
  (.setLevel *log* logging.INFO)
  (if (os.access (os.path.dirname *default-log-file*) os.W_OK)
    (setv handler (logging.FileHandler *default-log-file*))
    (setv handler (logging.FileHandler (os.path.expanduser "~/replica.log"))))
  (.setLevel handler logging.INFO)
  (setv formatter (logging.Formatter *default-log-format*))
  (.setFormatter handler formatter)
  (.addHandler *log* handler))

(defn disable-auto [fsys]
  ;
  ; Disable the auto-snapshot service for the given file system.
  ;
  ; :param fsys: file system on which to set property.
  ; :return: previous value for auto-snapshot propery.
  ;
  ;
  (setv output (zfs.get "-Ho" "value" "com.sun:auto-snapshot" fsys))
  (zfs.set "com.sun:auto-snapshot=false" fsys)
  (.info *log* (.format "disabled auto-snapshot on {}" fsys))
  (.strip output))

(defn restore-auto [fsys saved]
  ;
  ; Restore the auto-snapshot property to the previously set value.
  ;
  ; :param fsys: file system on which to set property.
  ; :param saved: previous value of auto-snapshot property
  ;
  ; zfs get returns '-' when the property is not set.
  (if (!= saved "-")
    (do
      (zfs.set (.format "com.sun:auto-snapshot={}" saved) fsys)
      (.info *log* (.format "set auto-snapshot to {} on {}" saved fsys)))))

(defn take-snapshot [fsys]
  ;
  ; Create a snapshot on the named file system.
  ;
  ; Creates a snapshot for fsys whose name is today's date and time in the
  ; following format: %Y-%m-%d-%H:%M, and returns that name. The time is
  ; in UTC.
  ;
  ; :param fsys: file system on which to create snapshot.
  ; :return: name of snapshot that was created.
  ;
  ; make a snapshot of the source file system with the date and time as the name
  (setv tag (.strftime (datetime.utcnow) "%Y-%m-%d-%H:%M"))
  (setv snap_name (.format "{}@replica:{}" fsys tag))
  (zfs.snapshot snap_name)
  (.info *log* (.format "created snapshot {}" snap_name))
  tag)

(defn our-snapshots [fsys]
  ;
  ; Return a list of the snapshots created by this script.
  ;
  ; Get our mananged snapshots for the given file system, such that they
  ; are named "replica:" followed by a date in the ISO 8601 format (i.e.
  ; YYYY-mm-dd-HH:MM).
  ;
  ; :param fsys: file system on which to find snapshots.
  ; :return: list of snapshot names.
  ;
  (.info *log* "fetching snapshots")
  (setv snaps (.splitlines (zfs.list "-t" "snapshot" "-Hr" fsys)))
  (setv prog (re.compile "@replica:\\d{4}-\\d{2}-\\d{2}-\\d{2}:\\d{2}"))
  (setv snaps (list-comp snap [snap snaps] (.search prog snap)))
  (setv snaps (list-comp (get (.split snap "\t") 0) [snap snaps]))
  (setv snaps (list-comp (get (.split snap "@") 1) [snap snaps]))
  (.sort snaps)
  snaps)

(defn send-snapshot [src dst tag]
  ;
  ; Send a replication stream for a single snapshot.
  ;
  ; :param src: source file system
  ; :param dst: destination file system
  ; :param tag: snapshot to be sent
  ;
  (.info *log* (.format "sending full snapshot from {} to {}" src dst))
  (setv send (apply subprocess.Popen
              ; Popen expects a list and apply takes a list, so nested lists
              [["zfs" "send" "-R" (.format "{}@{}" src tag)]]
              {"stdout" subprocess.PIPE}))
  (setv recv (apply subprocess.Popen
              ; Popen expects a list and apply takes a list, so nested lists
              [["zfs" "recv" "-F" dst]]
              {"stdin" send.stdout
               "stdout" subprocess.PIPE}))
  ; Allow send process to receive a SIGPIPE if recv exits early.
  (.close (. send stdout))
  ; Read the outputs so the process finishes, but ignore them.
  (.communicate recv)
  (.info *log* "full snapshot sent")
  (if (and (!= send.returncode 0)
           (not (is send.returncode None)))
    (raise (subprocess.CalledProcessError send.returncode "zfs send")))
  (if (and (!= recv.returncode 0)
           (not (is recv.returncode None)))
    (raise (subprocess.CalledProcessError recv.returncode "zfs recv"))))

(defn send-incremental [src dst tag1 tag2]
  ;
  ; Send an incremental replication stream from source to target.
  ;
  ; :param src: source file system
  ; :param dst: destination file system
  ; :param tag1: starting snapshot
  ; :param tag2: ending snapshot
  ;
  (.info *log* (.format "sending incremental snapshot from {} to {}" src dst))
  ; Tried this with python-sh but recv failed to read from send
  ; zfs.recv(zfs.send("-R", "-I", tag1, "{}@{}".format(src, tag2), _piped=True), "-F", dst)
  (setv send (apply subprocess.Popen
              ; Popen expects a list and apply takes a list, so nested lists
              [["zfs" "send" "-R" "-I" tag1 (.format "{}@{}" src tag2)]]
              {"stdout" subprocess.PIPE}))
  (setv recv (apply subprocess.Popen
              ; Popen expects a list and apply takes a list, so nested lists
              [["zfs" "recv" "-F" dst]]
              {"stdin" send.stdout
               "stdout" subprocess.PIPE}))
  ; Allow send process to receive a SIGPIPE if recv exits early.
  (.close (. send stdout))
  ; Read the outputs so the process finishes, but ignore them.
  (recv.communicate)
  (.info *log* "incremental snapshot sent")
  (if (and (!= send.returncode 0)
           (not (is send.returncode None)))
    (raise (subprocess.CalledProcessError send.returncode "zfs send")))
  (if (and (!= recv.returncode 0)
           (not (is recv.returncode None)))
    (raise (subprocess.CalledProcessError recv.returncode "zfs recv"))))

(defn create-and-send-snapshot [src dst]
  ;
  ; Create a snapshot and send it to the destination.
  ;
  ; :param src: source file system
  ; :param dst: destination file system
  ;
  ; make the new snapshot, get a list of existing snapshots,
  ; and decide whether to send a full stream or an incremental
  (take-snapshot src)
  (setv snaps (our-snapshots src))
  (if (or (is snaps None)
          (= (len snaps) 0))
    (raise (OSError (.format "Failed to create new snapshot in {}" src))))
  (setv dstsnaps (our-snapshots dst))
  (if (and (not (is dstsnaps None))
           (> (len dstsnaps) 0)
           (not (in (get dstsnaps -1) snaps)))
    (raise (OSError "Destination snapshots out of sync with source, destroy and try again.")))
  (cond [(= (len snaps) 1)
          ; send the initial snapshot
          (send-snapshot src dst (get snaps 0))]
        [(or (is dstsnaps None) (= (len dstsnaps) 0))
          ; send the latest snapshot since the destination has none
          (send-snapshot src dst (get snaps -1))]
        [True
          (do
            ; destination has matching snapshots, send an incremental
            (setv recent (slice snaps -2))
            (send-incremental src dst (get recent 0) (get recent 1)))]))

(defn prune-old-snapshots [src dst]
  ;
  ; Prune the old replica snapshots from source and destination.
  ;
  ; :param src: source file system
  ; :param dst: destination file system
  ;
  ; prune old snapshots in source file system
  (setv snaps (our-snapshots src))
  (setv oldsnaps (slice snaps 0 -2))
  (for [snap oldsnaps]
    (zfs.destroy (.format "{}@{}" src snap))
    (.info *log* (.format "deleted old snapshot {}" snap)))
  ; prune old snapshots in destination file system
  (setv dstsnaps (our-snapshots dst))
  (if (or (is dstsnaps None)
          (= (len dstsnaps) 0))
    (raise (OSError (.format "Failed to create new snapshot in {}" dst))))
  (setv oldsnaps (slice dstsnaps 0 -2))
  (for [snap oldsnaps]
    (zfs.destroy (.format "{}@{}" dst snap))
    (.info *log* (.format "deleted old snapshot {}" snap))))

(defmain [&rest args]
  (setv parser (apply argparse.ArgumentParser []
                {"description" "Sends snapshots from one ZFS dataset to another."}))
  (apply .add_argument
    [parser "src"]
    {"help" "Source ZFS file system"})
  (apply .add_argument
    [parser "dest"]
    {"help" "Destination ZFS file system"})
  (setv args (.parse_args parser))

  (configure-logging)

  ; disable the auto-snapshot service to prevent spurious failures
  (try
    (do
      (setv assrc (disable-auto args.src))
      (setv asdst (disable-auto args.dest)))
    (catch [cpe subprocess.CalledProcessError]
      (do
        (apply print ["Unable to acquire/modify auto-snapshot status."]
          {"file" sys.stderr})
        (if cpe.output
          (.write sys.stderr (.decode cpe.output)))
        (sys.exit cpe.returncode))))
  (try
    (do
      (create-and-send-snapshot args.src args.dest)
      (prune-old-snapshots args.src args.dest))
    (catch [cpe subprocess.CalledProcessError]
      (do
        (if cpe.output
          (.write sys.stderr (.decode cpe.output)))
        (sys.exit cpe.returncode)))
    (catch [ose OSError]
      (do
        (.write sys.stderr (str ose))
        (sys.exit os.EX_OSERR)))
    (finally
      (do
        ; restore the auto-snapshot property on the file systems
        (restore-auto args.dest asdst)
        (restore-auto args.src assrc)))))
