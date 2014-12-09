#!/usr/bin/env hy
;
; Find the total size of all files in the current directory tree,
; and compute the average file size in bytes. Symbolic links are
; ignored.
;

(import os)
(import [os.path [getsize islink join]])

(defn count-files []
  "Return the number of files found and their total byte count."
  (let [[total 0] [count 0]]
    (for [(, root dirs files) (os.walk ".")]
      (if (in ".git" dirs)
        (.remove dirs ".git"))
        (setv files (list-comp (join root name) [name files]))
        (setv files (list-comp name [name files] (not (islink name))))
        (setv count (+ count (len files)))
        (setv total (+ total (sum (list-comp (getsize name) [name files])))))
    (, total count)))

(defn count-all []
  "Compute the average file size for all files in the current tree."
  (setv (, total count) (count-files))
  (setv avg (/ total count))
  (print (.format "Total: {0}\nCount: {1}\nAverage: {2:.2f}" total count avg))
  0)

(defmain [&rest args]
  (count-all))
