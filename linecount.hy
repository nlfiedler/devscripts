#!/usr/bin/env hy
;
; Counts lines of code in Python scripts.
;
; Bascially a fixed version
; of http://code.activestate.com/recipes/527746-line-of-code-counter/
;

(import os)
(import fnmatch)

(defn walk [&optional [root "."] [recurse True] [pattern "*"]]
  ; Generator for walking a directory tree.
  ;
  ; Starts at specified root folder, returning files that match our
  ; pattern. Optionally will also recurse through directories.
  (for [(, path subdirs files) (os.walk root)]
    (for [name files]
      (if (fnmatch.fnmatch name pattern)
        (yield (os.path.join path name))))
    (if (not recurse)
      (break))))

(defn count [&optional [root "."] [recurse True]]
  ; Count lines of code.
  ;
  ; Returns maximal size (source LOC) with blank lines and comments as well
  ; as minimal size (logical LOC) stripping same.
  ;
  ; Sums all Python files in the specified folder. By default recurses
  ; through subfolders.
  (let [[file_count 0] [count_mini 0] [count_maxi 0]]
    (for [fspec (walk root recurse "*.py")]
      (setv skip False) ; nested (let) hides outer context?
      (with [[f (open fspec)]]
        (setv file_count (inc file_count))
        (for [line f]
          (setv count_maxi (inc count_maxi))
          (setv line (.strip line))
          (if line
            (if (not (.startswith line "#"))
              (if (= (.count line "\"\"\"") 1)
                (setv skip (not skip))
                (if (not skip)
                  (setv count_mini (inc count_mini)))))))))
    (, file_count count_mini count_maxi)))

(defmain [&rest args]
  (def (, files mini maxi) (count))
  (print (.format "File count: {}\nMaximal lines: {}\nMinimal lines: {}" files maxi mini)))
