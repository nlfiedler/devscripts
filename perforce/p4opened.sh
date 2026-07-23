#!/bin/sh
#
# Organize the output of `p4 opened` in a way that actually makes sense.
#
# Still not awesome, and no where near what Sapling does, but at least it's
# ordered by change number instead of depot path.
#

p4 -ztag opened | awk '/^\.\.\. change/{c=$3} /^\.\.\. depotFile/{f=$3} /^\.\.\. action/{print c, f, $3}' | sort -n
