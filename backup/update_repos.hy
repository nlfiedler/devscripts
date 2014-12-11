#!/usr/bin/env hy
;
; Finds and updates the Git repositories.
;
; This is a highly specialized script that assumes that the repositories
; in question are bare (i.e. no working tree) and have a single remote.
;
; To create the initial backup repositories, clone them like so:
;
; $ git clone --mirror <git_url>
;
; Requirements
; * python-sh (pip install sh)
;

(import os)
(import stat)
(import sys)

(import [sh [git]])

(defn get-directories [path]
  ;
  ; Generate a list of directoires in the given path.
  ;
  ; :param path: path to be visited.
  ;
  ; Yields each directory within path one by one.
  ;
  (for [entry (os.listdir path)]
    (setv pathname (os.path.join path entry))
    (setv mode (get (os.lstat pathname) stat.ST_MODE))
    (if (stat.S_ISDIR mode)
      (yield pathname))))

(defn git-remote [path]
  ;
  ; Return the (fetch) URL for the remote repository.
  ;
  ; :param path: path of the local Git repository.
  ;
  (setv output (.splitlines (git (.format "--git-dir={}" path) "remote")))
  (if (> (len output) 1)
    (do
      (sys.stderr.write (.format "Too much output from `git remote` for {}" path))
      (sys.exit os.EX_OSERR)))
  (setv remote (get output 0))
  (setv output (.splitlines (git (.format "--git-dir={}" path) "remote" "-v")))
  (setv fetch_url None)
  (for [line output]
      (if (and (.startswith line remote) (.endswith line " (fetch)"))
        (do
          (setv (, _ fetch_url _) (.split line))
          (break))))
  (, remote fetch_url))

(defmain [&rest args]
  (setv ignored_list [])
  (for [candidate (sorted (get-directories "."))]
    (if (os.path.exists (os.path.join candidate "HEAD"))
      (do
        (setv (, remote fetch_url) (git-remote candidate))
        (git (.format "--git-dir={}" candidate)  "fetch" remote)
        (print (.format "Fetched {} successfully for {}" fetch_url candidate)))
      (.append ignored_list candidate)))
  (for [ignored ignored_list]
    (print (.format "Ignored non-Git entry {}" ignored))))
