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
      (if (some (fn [ent] (= ".git" ent)) dirs)
        (.remove dirs ".git"))
        (def files (list-comp (join root name) [name files]))
        (def files (list-comp name [name files] (not (islink name))))
        (def count (+ count (.--len-- files)))
        (def total (+ total (sum (list-comp (getsize name) [name files]))))
      )
    (, total count)))

(defn count-all []
  "Compute the average file size for all files in the current tree."
  (def (, total count) (count-files))
  (def avg (/ total count))
  (print (.format "Total: {0}\nCount: {1}\nAverage: {2:.2f}" total count avg))
  0)

(defmain [&rest args]
  (count-all))
