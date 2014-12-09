#!/usr/bin/env hy
;
; Fix permissions of files and directories.
;
(import argparse)
(import os)
(import [stat [S_IMODE]])
(import sys)

(defn fix-perms [leading names perms]
  ;
  ; Fix permissions of a set of entities.
  ;
  ; :param leading: the leading path to the entities.
  ; :param names: list of file/dir entities to fix.
  ; :param perms: desired permissions.
  ;
  (for [name names]
    (setv fpath (os.path.join leading name))
    (setv fstat (os.stat fpath))
    (if (!= (S_IMODE (. fstat st_mode)) perms)
      (os.chmod fpath perms))))

(defmain [&rest args]
  ;
  ; Fix permissions of files and directories.
  ;
  (setv parser (apply argparse.ArgumentParser [] {
          "description" "Fix permissions of files and directories."}))
  (apply .add_argument [parser "-f" "--file"] {
          "default" "644"
          "help" "permissions for files (default 644)"})
  (apply .add_argument [parser "-d" "--dir"] {
          "default" "755"
          "help" "permissions for directories (default 755)"})
  (apply .add_argument [parser "-x" "--exclude"] {
          "nargs" "*"
          "help" "entries to ignore (can specify more than one)"})
  (apply .add_argument [parser "-p" "--path"] {
          "nargs" "*"
          "default" "."
          "help" "one or more paths to process (default .)"})
  (setv parsed (.parse_args parser))
  (setv fperms (int parsed.file 8))
  (setv dperms (int parsed.dir 8))
  (if (or (> fperms (int "0o777" 8))
          (< fperms (int "0o400" 8)))
    (do
      (print (.format "Invalid file permissions: {}" parsed.file))
      (sys.exit 1)))
  (if (or (> dperms (int "0o777" 8))
          (< dperms (int "0o400" 8)))
    (do
      (print (.format "Invalid directory permissions: {}" parsed.dir))
      (sys.exit 1)))
  (for [path parsed.path]
    (for [(, dirpath dirnames filenames) (os.walk path)]
      (if parsed.exclude
        (do
          (for [ii (range (- (len dirnames) 1) 0 -1)]
            (if (in (get dirnames ii) parsed.exclude)
              (.pop dirnames ii)))
          (for [ii (range (- (len filenames) 1) 0 -1)]
            (if (in (get filenames ii) parsed.exclude)
              (.pop filenames ii)))))
      (fix-perms dirpath filenames fperms)
      (fix-perms dirpath dirnames dperms))))
