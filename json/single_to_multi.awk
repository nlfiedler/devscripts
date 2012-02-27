#!/usr/bin/awk -f
#
# AWK script to convert a "JSON" document that consists of a single JSON
# formatted entry on each line to an array of comma-separated entries,
# parseable using JSON libraries.
#

BEGIN {
  # count the number of lines in the input file
  CMD = sprintf("wc -l %s", ARGV[1])
  CMD | getline WC
  split(WC, ARR, " ")
  LN = ARR[1]
  print "["
}

{
  if (NR == LN) {
    print $0
  } else {
    # for all but the last line, append a comma
    print $0 ","
  }
}

END {
  print "]"
}
