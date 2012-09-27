#!/usr/bin/env python3
#
# Copyright (c) 2012 Nathan Fiedler
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

#
# Python script to assign a Perforce job to the current Perforce user,
# ensuring that the job is not assigned to anyone else first. Marks the job
# as 'inprogress'.
#
# This script relies on the P4Python Perforce API bindings, which can be
# found at http://www.perforce.com/product/components/apis
#

import argparse
import sys

import P4


def grab_job(p4, num, user):
    """Check if the job is unassigned, and if so, assign to current user.
    Change the status to 'inprogress'.

    Keyword arguments:
    p4   -- P4 API
    num  -- job number
    user -- Perforce username of new job owner
    """
    job = p4.fetch_job(num)
    if job:
        if 'OwnedBy' in job:
            sys.stderr.write("job {} already owned by {}\n".format(
                    num, job['OwnedBy']))
        else:
            job['OwnedBy'] = user
            job['Status'] = 'inprogress'
            p4.save_job(job)
            print("Updated job {}".format(num))
    else:
        sys.stderr.write("warning: no such job {}\n".format(num))


def main():
    """Parse command line arguments and do the work.
    """
    desc = "Assigns a job to the current user, marks as 'inprogress'."
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument('jobs', metavar='J', nargs='+',
                        help='job number to be assigned')
    args = parser.parse_args()

    try:
        p4 = P4.P4()
        p4.connect()
        user = p4.fetch_user()
        if user:
            for job in args.jobs:
                grab_job(p4, job, user['User'])
        else:
            sys.stderr.write("Cannot retrieve current Perforce user\n")
    except P4.P4Exception as e:
        sys.stderr.write("error: p4 action failed: {}\n".format(e))


if __name__ == '__main__':
    main()
