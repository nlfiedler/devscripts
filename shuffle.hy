;
; Hylang script to shuffle the lines of a text file.
;

(import [os.path [basename]])
(import random)
(import sys)

(defn shuffle [args]
  (if (= (len args) 1)
    (do
      (print (.format "Usage: {} <inputfile>" (basename (first args))))
      1)
    (do
      (with [[f (open (second args))]]
        (def lines (.readlines f)))
      (random.shuffle lines)
      (list-comp (apply print [line] {"end" " "}) [line lines])
      0)))

(defmain [&rest args]
  (shuffle args))
