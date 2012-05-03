#!/usr/bin/awk -f
#
# AWK script to get the unique set of Subversion committers in a log file.
#

function ltrim(s) { sub(/^[ \t]+/, "", s); return s }
function rtrim(s) { sub(/[ \t]+$/, "", s); return s }
function trim(s)  { return rtrim(ltrim(s)); }

/^r[0-9]{1,5} \|/ {
  split($0, arr, "|")
  name = trim(arr[2])
  authors[name] += + 1
}

END {
  for (k in authors) {
    print k "," authors[k]
  }
}
