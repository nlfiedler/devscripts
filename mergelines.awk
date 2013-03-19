#!/usr/bin/awk -f
#
# AWK script to join multiple lines if the preceeding line ends with a comma (,).
#
# For example:
#
#   1,
#   2,
#   3
#
# Turns into:
#
#   1, 2, 3
#

/,$/ {
    ORS=""
    print $0
    do {
        getline
        print $0
    } while ($0 ~ /,$/)
    ORS="\n"
    print ""
}
