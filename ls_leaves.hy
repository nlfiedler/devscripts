;
; Find the leaf directories within the given set of paths (defaulting to the
; current working directory) and display the sorted result set.
;

(import os)
(import sys)

(defn find-leaves [args]
  ; If arguments are given, use them as a starting point.
  (def paths
    (if (> (.--len-- args) 1)
      (rest args)
      (, ".")))
  ; Walk the directory tree looking for directories with no subdirectories.
  (def leaves '())
  (for [path paths]
    (for [(, root dirs files) (os.walk path)]
      (if (= (.--len-- dirs) 0)
        (.append leaves
          (if (.startswith root "./")
            (slice root 2)
            root)))))
  ; Sort the results and output.
  (.sort leaves)
  (list-comp (print leaf) [leaf leaves]))

(defmain [&rest args]
  (find-leaves args))
